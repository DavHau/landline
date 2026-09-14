from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NETWORK = r'''use std::{
    collections::{HashMap, HashSet},
    fs,
    path::PathBuf,
    sync::mpsc::{self, Receiver},
};

use anyhow::{Context, Result};
use iroh::{
    endpoint::{presets, Connection},
    Endpoint, EndpointId, SecretKey,
};
use serde::{Deserialize, Serialize};
use tokio::{sync::mpsc as tokio_mpsc, task::JoinHandle};

use crate::wire::{self, Kind};

const MAX_REMOTE_PEERS: usize = 7;

#[derive(Debug)]
pub enum Command {
    Connect(String),
    Disconnect,
    BeginTransmit,
    Audio(Vec<u8>),
    EndTransmit,
    SetProfile { name: String, avatar_data: Option<String> },
    Shutdown,
}

#[derive(Debug)]
pub enum Event {
    EndpointReady(String),
    Connected,
    Disconnected,
    Peer { id: String, name: String, avatar_data: Option<String> },
    PeerDisconnected(String),
    RemoteTransmit { id: String, active: bool },
    RemoteAudio { id: String, packet: Vec<u8> },
    LocalTransmitRevoked,
    Error(String),
}

pub struct Handle {
    pub commands: tokio_mpsc::UnboundedSender<Command>,
    pub events: Receiver<Event>,
}

impl Handle {
    pub fn spawn(name: String, avatar_data: Option<String>) -> Self {
        let (command_tx, command_rx) = tokio_mpsc::unbounded_channel();
        let (event_tx, event_rx) = mpsc::channel();

        std::thread::Builder::new()
            .name("landline-iroh".into())
            .spawn(move || {
                let runtime = tokio::runtime::Builder::new_multi_thread()
                    .enable_all()
                    .thread_name("landline-iroh-worker")
                    .build();

                match runtime {
                    Ok(runtime) => {
                        if let Err(error) = runtime.block_on(run(command_rx, event_tx.clone(), name, avatar_data)) {
                            let _ = event_tx.send(Event::Error(error.to_string()));
                        }
                    }
                    Err(error) => {
                        let _ = event_tx.send(Event::Error(format!("Unable to start Iroh runtime: {error}")));
                    }
                }
            })
            .expect("failed to spawn Landline Iroh thread");

        Self {
            commands: command_tx,
            events: event_rx,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct HelloMessage {
    endpoint_id: String,
    name: String,
    avatar_kind: String,
    avatar_data: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct MembershipMessage {
    endpoint_ids: Vec<String>,
}

struct Session {
    id: u64,
    peer_id: Option<String>,
    initiated_locally: bool,
    frames: tokio_mpsc::UnboundedSender<Vec<u8>>,
    task: JoinHandle<()>,
}

enum Internal {
    Incoming(Connection),
    AcceptError(String),
    Frame { id: u64, frame: wire::Frame },
    SessionEnded { id: u64, error: Option<String> },
}

async fn run(
    mut commands: tokio_mpsc::UnboundedReceiver<Command>,
    events: mpsc::Sender<Event>,
    mut local_name: String,
    mut local_avatar_data: Option<String>,
) -> Result<()> {
    let secret = load_or_create_secret()?;
    let endpoint = Endpoint::builder(presets::N0)
        .secret_key(secret)
        .alpns(vec![wire::ALPN.to_vec()])
        .bind()
        .await
        .context("unable to bind the Iroh endpoint")?;

    let endpoint_id = endpoint.id().to_string();
    let _ = events.send(Event::EndpointReady(endpoint_id.clone()));

    let (internal_tx, mut internal_rx) = tokio_mpsc::unbounded_channel();
    let accept_endpoint = endpoint.clone();
    let accept_tx = internal_tx.clone();
    let accept_task = tokio::spawn(async move {
        while let Some(incoming) = accept_endpoint.accept().await {
            let tx = accept_tx.clone();
            tokio::spawn(async move {
                match incoming.await {
                    Ok(connection) => {
                        let _ = tx.send(Internal::Incoming(connection));
                    }
                    Err(error) => {
                        let _ = tx.send(Internal::AcceptError(error.to_string()));
                    }
                }
            });
        }
    });

    let mut sessions: HashMap<u64, Session> = HashMap::new();
    let mut connecting: HashSet<String> = HashSet::new();
    let mut next_session_id = 1_u64;
    let mut local_transmit = false;
    let mut remote_speaker: Option<String> = None;

    loop {
        tokio::select! {
            command = commands.recv() => {
                let Some(command) = command else { break; };
                match command {
                    Command::Connect(raw) => {
                        let peer_id = normalize_endpoint_id(&raw);
                        if peer_id.is_empty() || peer_id == endpoint_id || has_peer(&sessions, &peer_id) || connecting.contains(&peer_id) {
                            continue;
                        }
                        if known_peer_ids(&sessions).len() >= MAX_REMOTE_PEERS {
                            let _ = events.send(Event::Error("Landline already has seven remote users.".into()));
                            continue;
                        }

                        connecting.insert(peer_id.clone());
                        match open_outgoing_session(
                            &endpoint,
                            next_session_id,
                            &peer_id,
                            &endpoint_id,
                            &local_name,
                            local_avatar_data.as_deref(),
                            internal_tx.clone(),
                        ).await {
                            Ok(session) => {
                                next_session_id = next_session_id.wrapping_add(1);
                                sessions.insert(session.id, session);
                                connecting.remove(&peer_id);
                            }
                            Err(error) => {
                                connecting.remove(&peer_id);
                                let _ = events.send(Event::Error(format!("Unable to connect: {error}")));
                            }
                        }
                    }
                    Command::Disconnect => {
                        local_transmit = false;
                        if let Some(id) = remote_speaker.take() {
                            let _ = events.send(Event::RemoteTransmit { id, active: false });
                        }
                        let ids: Vec<u64> = sessions.keys().copied().collect();
                        for id in ids {
                            remove_session(&mut sessions, id, true, &events);
                        }
                        connecting.clear();
                        let _ = events.send(Event::Disconnected);
                    }
                    Command::BeginTransmit => {
                        if remote_speaker.is_some() {
                            let _ = events.send(Event::LocalTransmitRevoked);
                            continue;
                        }
                        local_transmit = true;
                        broadcast_frame(&sessions, Kind::PttBegin, &[], &events);
                    }
                    Command::Audio(packet) => {
                        if local_transmit {
                            broadcast_frame(&sessions, Kind::Audio, &packet, &events);
                        }
                    }
                    Command::EndTransmit => {
                        if local_transmit {
                            local_transmit = false;
                            broadcast_frame(&sessions, Kind::PttEnd, &[], &events);
                        }
                    }
                    Command::SetProfile { name, avatar_data } => {
                        local_name = normalize_name(&name);
                        local_avatar_data = avatar_data;
                        if let Ok(payload) = hello_payload(&endpoint_id, &local_name, local_avatar_data.as_deref()) {
                            broadcast_frame(&sessions, Kind::Hello, &payload, &events);
                        }
                    }
                    Command::Shutdown => break,
                }
            }
            internal = internal_rx.recv() => {
                let Some(internal) = internal else { break; };
                match internal {
                    Internal::Incoming(connection) => {
                        if sessions.len() >= MAX_REMOTE_PEERS + 2 {
                            drop(connection);
                            continue;
                        }
                        match open_incoming_session(
                            connection,
                            next_session_id,
                            &endpoint_id,
                            &local_name,
                            local_avatar_data.as_deref(),
                            internal_tx.clone(),
                        ).await {
                            Ok(session) => {
                                next_session_id = next_session_id.wrapping_add(1);
                                sessions.insert(session.id, session);
                            }
                            Err(error) => {
                                let _ = events.send(Event::Error(format!("Unable to accept Landline stream: {error}")));
                            }
                        }
                    }
                    Internal::AcceptError(error) => {
                        tracing::warn!(%error, "Iroh incoming connection failed");
                    }
                    Internal::Frame { id, frame } => {
                        if !sessions.contains_key(&id) {
                            continue;
                        }
                        match frame.kind {
                            Kind::Hello => {
                                let Ok(hello) = serde_json::from_slice::<HelloMessage>(&frame.payload) else { continue; };
                                let remote_id = normalize_endpoint_id(&hello.endpoint_id);
                                if remote_id.is_empty() || remote_id == endpoint_id {
                                    remove_session(&mut sessions, id, false, &events);
                                    continue;
                                }

                                let duplicate_ids: Vec<u64> = sessions.iter()
                                    .filter_map(|(other_id, session)| {
                                        (*other_id != id && session.peer_id.as_deref() == Some(remote_id.as_str())).then_some(*other_id)
                                    })
                                    .collect();

                                if !duplicate_ids.is_empty() {
                                    let should_keep_locally_initiated = endpoint_id < remote_id;
                                    let current_is_local = sessions.get(&id).is_some_and(|s| s.initiated_locally);
                                    if current_is_local == should_keep_locally_initiated {
                                        for duplicate_id in duplicate_ids {
                                            remove_session(&mut sessions, duplicate_id, false, &events);
                                        }
                                    } else {
                                        remove_session(&mut sessions, id, false, &events);
                                        continue;
                                    }
                                }

                                if let Some(session) = sessions.get_mut(&id) {
                                    session.peer_id = Some(remote_id.clone());
                                }
                                connecting.remove(&remote_id);

                                if known_peer_ids(&sessions).len() > MAX_REMOTE_PEERS {
                                    remove_session(&mut sessions, id, false, &events);
                                    continue;
                                }

                                let avatar_data = if hello.avatar_kind == "jpeg" { hello.avatar_data } else { None };
                                let _ = events.send(Event::Peer {
                                    id: remote_id.clone(),
                                    name: normalize_name(&hello.name),
                                    avatar_data,
                                });
                                let _ = events.send(Event::Connected);

                                if local_transmit {
                                    send_frame_to(&sessions, id, Kind::PttBegin, &[], &events);
                                }
                                broadcast_membership(&sessions, &endpoint_id, &events);
                            }
                            Kind::PttBegin => {
                                let Some(peer_id) = sessions.get(&id).and_then(|s| s.peer_id.clone()) else { continue; };
                                if local_transmit {
                                    if peer_id < endpoint_id {
                                        local_transmit = false;
                                        if let Some(old) = remote_speaker.replace(peer_id.clone()) {
                                            if old != peer_id {
                                                let _ = events.send(Event::RemoteTransmit { id: old, active: false });
                                            }
                                        }
                                        let _ = events.send(Event::LocalTransmitRevoked);
                                        let _ = events.send(Event::RemoteTransmit { id: peer_id, active: true });
                                        broadcast_frame(&sessions, Kind::PttEnd, &[], &events);
                                    }
                                } else {
                                    let should_take_floor = match remote_speaker.as_deref() {
                                        None => true,
                                        Some(current) => peer_id.as_str() < current,
                                    };
                                    if should_take_floor {
                                        if let Some(old) = remote_speaker.replace(peer_id.clone()) {
                                            if old != peer_id {
                                                let _ = events.send(Event::RemoteTransmit { id: old, active: false });
                                            }
                                        }
                                        let _ = events.send(Event::RemoteTransmit { id: peer_id, active: true });
                                    }
                                }
                            }
                            Kind::Audio => {
                                let Some(peer_id) = sessions.get(&id).and_then(|s| s.peer_id.clone()) else { continue; };
                                if !local_transmit && remote_speaker.as_deref() == Some(peer_id.as_str()) {
                                    let _ = events.send(Event::RemoteAudio { id: peer_id, packet: frame.payload });
                                }
                            }
                            Kind::PttEnd => {
                                let Some(peer_id) = sessions.get(&id).and_then(|s| s.peer_id.clone()) else { continue; };
                                if remote_speaker.as_deref() == Some(peer_id.as_str()) {
                                    remote_speaker = None;
                                    let _ = events.send(Event::RemoteTransmit { id: peer_id, active: false });
                                }
                            }
                            Kind::Ping => {
                                send_frame_to(&sessions, id, Kind::Pong, &frame.payload, &events);
                            }
                            Kind::Pong => {}
                            Kind::Membership => {
                                let Ok(membership) = serde_json::from_slice::<MembershipMessage>(&frame.payload) else { continue; };
                                let mut candidates: Vec<String> = membership.endpoint_ids
                                    .into_iter()
                                    .map(|candidate| normalize_endpoint_id(&candidate))
                                    .filter(|candidate| !candidate.is_empty() && candidate != &endpoint_id)
                                    .collect();
                                candidates.sort();
                                candidates.dedup();
                                candidates.truncate(MAX_REMOTE_PEERS);

                                for peer_id in candidates {
                                    if has_peer(&sessions, &peer_id) || connecting.contains(&peer_id) || endpoint_id >= peer_id {
                                        continue;
                                    }
                                    if known_peer_ids(&sessions).len() + connecting.len() >= MAX_REMOTE_PEERS {
                                        break;
                                    }
                                    connecting.insert(peer_id.clone());
                                    match open_outgoing_session(
                                        &endpoint,
                                        next_session_id,
                                        &peer_id,
                                        &endpoint_id,
                                        &local_name,
                                        local_avatar_data.as_deref(),
                                        internal_tx.clone(),
                                    ).await {
                                        Ok(session) => {
                                            next_session_id = next_session_id.wrapping_add(1);
                                            sessions.insert(session.id, session);
                                        }
                                        Err(error) => {
                                            tracing::warn!(%peer_id, %error, "unable to connect discovered Landline peer");
                                        }
                                    }
                                    connecting.remove(&peer_id);
                                }
                            }
                        }
                    }
                    Internal::SessionEnded { id, error } => {
                        let peer_id = sessions.get(&id).and_then(|session| session.peer_id.clone());
                        remove_session(&mut sessions, id, true, &events);
                        if let Some(peer_id) = peer_id {
                            connecting.remove(&peer_id);
                            if remote_speaker.as_deref() == Some(peer_id.as_str()) {
                                remote_speaker = None;
                                let _ = events.send(Event::RemoteTransmit { id: peer_id, active: false });
                            }
                        }
                        if let Some(error) = error {
                            tracing::warn!(%error, "Landline peer session ended");
                        }
                        if known_peer_ids(&sessions).is_empty() {
                            let _ = events.send(Event::Disconnected);
                        } else {
                            broadcast_membership(&sessions, &endpoint_id, &events);
                        }
                    }
                }
            }
        }
    }

    let ids: Vec<u64> = sessions.keys().copied().collect();
    for id in ids {
        remove_session(&mut sessions, id, false, &events);
    }
    accept_task.abort();
    endpoint.close().await;
    Ok(())
}

async fn open_outgoing_session(
    endpoint: &Endpoint,
    id: u64,
    peer_id: &str,
    endpoint_id: &str,
    local_name: &str,
    local_avatar_data: Option<&str>,
    internal: tokio_mpsc::UnboundedSender<Internal>,
) -> Result<Session> {
    let peer: EndpointId = peer_id.parse().context("invalid peer endpoint ID")?;
    let connection = endpoint.connect(peer, wire::ALPN).await?;
    start_session(
        id,
        connection,
        true,
        Some(peer_id.to_string()),
        endpoint_id,
        local_name,
        local_avatar_data,
        internal,
    ).await
}

async fn open_incoming_session(
    connection: Connection,
    id: u64,
    endpoint_id: &str,
    local_name: &str,
    local_avatar_data: Option<&str>,
    internal: tokio_mpsc::UnboundedSender<Internal>,
) -> Result<Session> {
    start_session(
        id,
        connection,
        false,
        None,
        endpoint_id,
        local_name,
        local_avatar_data,
        internal,
    ).await
}

async fn start_session(
    id: u64,
    connection: Connection,
    outgoing: bool,
    expected_peer_id: Option<String>,
    endpoint_id: &str,
    local_name: &str,
    local_avatar_data: Option<&str>,
    internal: tokio_mpsc::UnboundedSender<Internal>,
) -> Result<Session> {
    let (mut send, mut recv) = if outgoing {
        connection.open_bi().await?
    } else {
        connection.accept_bi().await?
    };

    let hello = wire::encode(Kind::Hello, &hello_payload(endpoint_id, local_name, local_avatar_data)?)?;
    send.write_all(&hello).await?;

    let (frame_tx, mut frame_rx) = tokio_mpsc::unbounded_channel::<Vec<u8>>();
    let task_internal = internal.clone();
    let task = tokio::spawn(async move {
        let result: Result<()> = async {
            loop {
                tokio::select! {
                    outgoing = frame_rx.recv() => {
                        let Some(frame) = outgoing else { break; };
                        send.write_all(&frame).await?;
                    }
                    incoming = wire::read(&mut recv) => {
                        let frame = incoming?;
                        if task_internal.send(Internal::Frame { id, frame }).is_err() {
                            break;
                        }
                    }
                }
            }
            Ok(())
        }.await;

        let _ = internal.send(Internal::SessionEnded {
            id,
            error: result.err().map(|error| format!("Landline connection ended: {error}")),
        });
        drop(connection);
    });

    Ok(Session {
        id,
        peer_id: expected_peer_id,
        initiated_locally: outgoing,
        frames: frame_tx,
        task,
    })
}

fn send_frame_to(
    sessions: &HashMap<u64, Session>,
    session_id: u64,
    kind: Kind,
    payload: &[u8],
    events: &mpsc::Sender<Event>,
) {
    let Some(session) = sessions.get(&session_id) else { return; };
    match wire::encode(kind, payload) {
        Ok(frame) => {
            if session.frames.send(frame).is_err() {
                let _ = events.send(Event::Error("Landline connection is no longer writable".into()));
            }
        }
        Err(error) => {
            let _ = events.send(Event::Error(error.to_string()));
        }
    }
}

fn broadcast_frame(
    sessions: &HashMap<u64, Session>,
    kind: Kind,
    payload: &[u8],
    events: &mpsc::Sender<Event>,
) {
    let ids: Vec<u64> = sessions.iter()
        .filter_map(|(id, session)| session.peer_id.as_ref().map(|_| *id))
        .collect();
    for id in ids {
        send_frame_to(sessions, id, kind, payload, events);
    }
}

fn broadcast_membership(
    sessions: &HashMap<u64, Session>,
    endpoint_id: &str,
    events: &mpsc::Sender<Event>,
) {
    let mut endpoint_ids = known_peer_ids(sessions);
    endpoint_ids.push(endpoint_id.to_string());
    endpoint_ids.sort();
    endpoint_ids.dedup();
    endpoint_ids.truncate(MAX_REMOTE_PEERS + 1);
    if let Ok(payload) = serde_json::to_vec(&MembershipMessage { endpoint_ids }) {
        broadcast_frame(sessions, Kind::Membership, &payload, events);
    }
}

fn remove_session(
    sessions: &mut HashMap<u64, Session>,
    id: u64,
    clear_peer: bool,
    events: &mpsc::Sender<Event>,
) {
    let Some(session) = sessions.remove(&id) else { return; };
    let peer_id = session.peer_id.clone();
    session.task.abort();
    if clear_peer {
        if let Some(peer_id) = peer_id {
            let still_present = sessions.values().any(|candidate| candidate.peer_id.as_deref() == Some(peer_id.as_str()));
            if !still_present {
                let _ = events.send(Event::PeerDisconnected(peer_id));
            }
        }
    }
}

fn has_peer(sessions: &HashMap<u64, Session>, peer_id: &str) -> bool {
    sessions.values().any(|session| session.peer_id.as_deref() == Some(peer_id))
}

fn known_peer_ids(sessions: &HashMap<u64, Session>) -> Vec<String> {
    let mut ids: Vec<String> = sessions.values().filter_map(|session| session.peer_id.clone()).collect();
    ids.sort();
    ids.dedup();
    ids
}

fn hello_payload(endpoint_id: &str, name: &str, avatar_data: Option<&str>) -> Result<Vec<u8>> {
    Ok(serde_json::to_vec(&HelloMessage {
        endpoint_id: endpoint_id.to_string(),
        name: normalize_name(name),
        avatar_kind: if avatar_data.is_some() { "jpeg".into() } else { "default".into() },
        avatar_data: avatar_data.map(ToOwned::to_owned),
    })?)
}

fn normalize_endpoint_id(value: &str) -> String {
    value.trim().chars().take(80).collect()
}

fn normalize_name(name: &str) -> String {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        "Caller".into()
    } else {
        trimmed.chars().take(48).collect()
    }
}

fn key_path() -> Result<PathBuf> {
    let root = dirs::data_local_dir().context("unable to find the local data directory")?;
    Ok(root.join("landline").join("iroh-secret.key"))
}

fn load_or_create_secret() -> Result<SecretKey> {
    let path = key_path()?;
    if let Ok(bytes) = fs::read(&path) {
        if let Ok(raw) = <[u8; 32]>::try_from(bytes.as_slice()) {
            return Ok(SecretKey::from_bytes(&raw));
        }
    }

    let secret = SecretKey::generate();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&path, secret.to_bytes())?;
    Ok(secret)
}
'''


def between(text: str, start: str, end: str, replacement: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + text[b:]


network = ROOT / "LandlineNix/src/network.rs"
network.write_text(NETWORK)

wire = ROOT / "LandlineNix/src/wire.rs"
text = wire.read_text()
text = text.replace('pub const ALPN: &[u8] = b"landline-iroh-audio/1";', 'pub const ALPN: &[u8] = b"landline-iroh-audio/2";')
text = text.replace('    Pong = 6,\n}', '    Pong = 6,\n    Membership = 7,\n}')
text = text.replace('            6 => Ok(Self::Pong),\n            _ =>', '            6 => Ok(Self::Pong),\n            7 => Ok(Self::Membership),\n            _ =>')
wire.write_text(text)

ui = ROOT / "LandlineNix/src/ui.rs"
text = ui.read_text()

stored = '''#[derive(Debug, Clone, Serialize, Deserialize)]
struct StoredProfile {
    name: String,
    #[serde(default)]
    avatar_data: Option<String>,
}
'''
remote = stored + '''
struct RemotePeer {
    id: String,
    name: String,
    avatar_data: Option<String>,
    avatar_texture: Option<TextureHandle>,
}
'''
text = text.replace(stored, remote)

text = text.replace('''    connected: bool,
    peer_id: String,
    peer_name: String,
    peer_avatar_data: Option<String>,
    peer_avatar_texture: Option<TextureHandle>,
    remote_talking: bool,
''', '''    connected: bool,
    peers: Vec<RemotePeer>,
    remote_speaker_id: Option<String>,
''')

text = text.replace('''            connected: false,
            peer_id: String::new(),
            peer_name: String::new(),
            peer_avatar_data: None,
            peer_avatar_texture: None,
            remote_talking: false,
''', '''            connected: false,
            peers: Vec::new(),
            remote_speaker_id: None,
''')

poll = r'''    fn poll_network(&mut self, ctx: &egui::Context) {
        while let Ok(event) = self.network.events.try_recv() {
            match event {
                Event::EndpointReady(id) => self.endpoint_id = id,
                Event::Connected => {
                    self.connected = true;
                    self.error = None;
                }
                Event::Disconnected => {
                    self.connected = false;
                    self.remote_speaker_id = None;
                    self.peers.clear();
                    self.stop_transmit();
                }
                Event::Peer { id, name, avatar_data } => {
                    let texture = avatar_data.as_deref().and_then(|data| {
                        texture_from_avatar_data(ctx, &format!("peer-avatar-{id}"), data)
                    });
                    if let Some(peer) = self.peers.iter_mut().find(|peer| peer.id == id) {
                        peer.name = name;
                        peer.avatar_data = avatar_data;
                        peer.avatar_texture = texture;
                    } else if self.peers.len() < 7 {
                        self.peers.push(RemotePeer {
                            id,
                            name,
                            avatar_data,
                            avatar_texture: texture,
                        });
                    }
                    self.connected = !self.peers.is_empty();
                }
                Event::PeerDisconnected(id) => {
                    self.peers.retain(|peer| peer.id != id);
                    if self.remote_speaker_id.as_deref() == Some(id.as_str()) {
                        self.remote_speaker_id = None;
                    }
                    self.connected = !self.peers.is_empty();
                }
                Event::RemoteTransmit { id, active } => {
                    if active {
                        self.remote_speaker_id = Some(id);
                    } else if self.remote_speaker_id.as_deref() == Some(id.as_str()) {
                        self.remote_speaker_id = None;
                    }
                }
                Event::RemoteAudio { id, packet } => {
                    if !self.local_talking && self.remote_speaker_id.as_deref() == Some(id.as_str()) {
                        if let Some(playback) = &self.playback {
                            if let Err(error) = playback.enqueue_network_packet(&packet) {
                                tracing::warn!(%error, "invalid remote audio packet");
                            }
                        }
                    }
                }
                Event::LocalTransmitRevoked => {
                    self.capture = None;
                    self.local_talking = false;
                    self.meter_level = 0.0;
                }
                Event::Error(error) => self.error = Some(error),
            }
        }
    }

'''
text = between(text, '    fn poll_network', '    fn begin_transmit', poll)
text = text.replace('if !self.connected || self.remote_talking || self.local_talking {', 'if self.endpoint_id.is_empty() || self.remote_speaker_id.is_some() || self.local_talking {')

status = r'''    fn status_text(&self, ptt_hovered: bool, remote_hovered: Option<&str>) -> String {
        if let Some(error) = &self.error {
            return error.clone();
        }
        if self.local_talking {
            return "You are talking".into();
        }
        if let Some(speaker_id) = self.remote_speaker_id.as_deref() {
            return format!("{} is talking", self.peer_display_name(speaker_id));
        }
        if let Some(name) = remote_hovered {
            return format!("{} is online", name);
        }
        if ptt_hovered {
            return if self.endpoint_id.is_empty() { "Starting Iroh…" } else { "Click to talk" }.into();
        }
        if self.connected {
            "You are muted".into()
        } else if self.endpoint_id.is_empty() {
            "Starting Iroh…".into()
        } else {
            "Ready — waiting for peers".into()
        }
    }

    fn peer_display_name(&self, id: &str) -> &str {
        self.peers
            .iter()
            .find(|peer| peer.id == id)
            .map(|peer| if peer.name.trim().is_empty() { "Caller" } else { peer.name.as_str() })
            .unwrap_or("Caller")
    }

'''
text = between(text, '    fn status_text', '    fn save_profile', status)

radio = r'''    fn paint_radio(&mut self, ui: &mut egui::Ui, canvas: Rect) -> (bool, Option<String>) {
        let painter = ui.painter();
        let radio = design_rect(canvas, 24.0, 96.0, 272.0, 272.0);
        painter.circle_filled(radio.center(), 136.0, PANEL);

        let dial_center = radio.center();
        let mut remote_hovered: Option<String> = None;
        for index in 0..8 {
            let angle = (index as f32 / 8.0) * std::f32::consts::TAU - std::f32::consts::FRAC_PI_2;
            let center = dial_center + vec2(angle.cos() * 88.0, angle.sin() * 88.0);
            let avatar_rect = Rect::from_center_size(center, vec2(48.0, 48.0));

            if index == 0 {
                painter.circle_filled(center, 24.0, Color32::from_rgb(64, 77, 79));
                if let Some(texture) = &self.profile_avatar_texture {
                    painter.image(texture.id(), avatar_rect, Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0)), Color32::WHITE);
                } else {
                    paint_initials(painter, center, &self.profile_name, Color32::WHITE);
                }
                if self.local_talking {
                    self.paint_talking_badge(painter, center + vec2(20.0, 20.0));
                }
            } else if let Some(peer) = self.peers.get(index - 1) {
                let response = ui.interact(avatar_rect, Id::new(("remote-avatar", index)), Sense::hover());
                if response.hovered() {
                    remote_hovered = Some(if peer.name.trim().is_empty() { "Caller".into() } else { peer.name.clone() });
                }
                painter.circle_filled(center, 24.0, Color32::from_rgb(64, 77, 79));
                if let Some(texture) = &peer.avatar_texture {
                    painter.image(texture.id(), avatar_rect, Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0)), Color32::WHITE);
                } else {
                    paint_initials(painter, center, if peer.name.trim().is_empty() { "Caller" } else { &peer.name }, Color32::WHITE);
                }
                if self.remote_speaker_id.as_deref() == Some(peer.id.as_str()) && !self.local_talking {
                    self.paint_talking_badge(painter, center + vec2(20.0, 20.0));
                }
            } else {
                painter.circle_filled(center, 24.0, Color32::BLACK);
            }
        }

        let ptt_center = dial_center;
        let ptt_rect = Rect::from_center_size(ptt_center, vec2(88.0, 88.0));
        let ptt_response = ui.interact(ptt_rect, Id::new("ptt"), Sense::click_and_drag());
        let ptt_down = ptt_response.is_pointer_button_down_on();
        if ptt_down != self.ptt_was_down {
            self.ptt_was_down = ptt_down;
            if ptt_down {
                self.begin_transmit();
            } else {
                self.stop_transmit();
            }
        }

        let scale = if ptt_response.hovered() || ptt_down || self.local_talking { 1.04 } else { 1.0 };
        painter.circle_filled(ptt_center, 40.0 * scale, if self.local_talking { GREEN } else { RED });
        let ptt_icon = Rect::from_center_size(ptt_center, vec2(24.0, 24.0) * scale);
        if self.local_talking {
            egui::Image::new(egui::include_image!("../assets/mic_on.svg"))
                .fit_to_exact_size(ptt_icon.size())
                .paint_at(ui, ptt_icon);
        } else {
            egui::Image::new(egui::include_image!("../assets/mic_muted.svg"))
                .fit_to_exact_size(ptt_icon.size())
                .paint_at(ui, ptt_icon);
        }

        (ptt_response.hovered(), remote_hovered)
    }

'''
text = between(text, '    fn paint_radio', '    fn paint_talking_badge', radio)

status_paint = r'''    fn paint_status(&self, ui: &mut egui::Ui, canvas: Rect, ptt_hovered: bool, remote_hovered: Option<&str>) {
        let painter = ui.painter();
        let rect = design_rect(canvas, 24.0, 408.0, 272.0, 48.0);
        painter.rect_filled(rect, 16.0, PANEL);
        painter.circle_filled(rect.min + vec2(20.0, 24.0), 4.0, if !self.endpoint_id.is_empty() { GREEN } else { INACTIVE });
        painter.text(
            rect.min + vec2(37.0, 24.0),
            Align2::LEFT_CENTER,
            self.status_text(ptt_hovered, remote_hovered),
            FontId::proportional(10.0),
            TEXT_SOFT,
        );
    }

'''
text = between(text, '    fn paint_status', '    fn paint_volume', status_paint)

settings = r'''    fn paint_settings_sheet(&mut self, ui: &mut egui::Ui, canvas: Rect) {
        let sheet = design_rect(canvas, 0.0, 88.0, 320.0, 584.0);
        paint_sheet_shadow(ui.painter(), sheet);
        ui.painter().rect_filled(sheet, 16.0, Color32::from_rgba_unmultiplied(255, 255, 255, 246));
        ui.allocate_ui_at_rect(sheet.shrink2(vec2(24.0, 20.0)), |ui| {
            ui.visuals_mut().override_text_color = Some(Color32::from_rgb(23, 23, 23));
            ui.heading("Iroh connection");
            ui.add_space(18.0);
            ui.label("This NixOS endpoint ID");
            let mut own_id = self.endpoint_id.clone();
            ui.add_sized([272.0, 64.0], egui::TextEdit::multiline(&mut own_id).interactive(false));
            ui.add_space(14.0);
            ui.label("Peer endpoint ID");
            ui.add_sized([272.0, 64.0], egui::TextEdit::multiline(&mut self.peer_input));
            ui.add_space(12.0);
            if ui.add_sized([272.0, 40.0], egui::Button::new("Add peer")).clicked() {
                let _ = self.network.commands.send(Command::Connect(self.peer_input.clone()));
                self.error = None;
            }
            if self.connected && ui.add_sized([272.0, 36.0], egui::Button::new("Disconnect all")).clicked() {
                let _ = self.network.commands.send(Command::Disconnect);
            }
            ui.add_space(14.0);
            ui.label(format!("State: {}", if self.connected { "Connected" } else { "Waiting" }));
            ui.label(format!("Connected peers: {}", self.peers.len()));
            for peer in self.peers.iter().take(7) {
                let name = if peer.name.trim().is_empty() { "Caller" } else { &peer.name };
                ui.small(format!("• {name}"));
            }
            ui.add_space(12.0);
            ui.small("Add one endpoint ID to seed the group. Protocol v2 membership discovery connects the remaining peers directly.");
        });

        let close_rect = Rect::from_min_size(sheet.min + vec2(280.0, 8.0), vec2(32.0, 32.0));
        if ui.interact(close_rect, Id::new("settings-close"), Sense::click()).clicked() {
            self.show_settings = false;
        }
        ui.painter().text(close_rect.center(), Align2::CENTER_CENTER, "×", FontId::proportional(20.0), Color32::from_rgb(23, 23, 23));
    }
'''
text = between(text, '    fn paint_settings_sheet', '\n}\n\nimpl Drop for LandlineApp', settings)
text = text.replace('self.paint_status(ui, canvas, ptt_hovered, remote_hovered);', 'self.paint_status(ui, canvas, ptt_hovered, remote_hovered.as_deref());')

ui.write_text(text)
print("Applied NixOS multi-user protocol v2 port")
