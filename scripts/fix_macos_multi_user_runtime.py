from pathlib import Path
import shutil


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path} but found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


iroh = Path("LandlineMac/IrohClient.swift")
content = Path("LandlineMac/ContentView.swift")

replace_once(
    iroh,
    """    private var sessions: [UUID: PeerSession] = [:]\n    private var connectingPeerIDs: Set<String> = []\n    private var preferredSlotByPeerID: [String: Int] = [:]\n    private var diagnosticSessionID: UUID?\n""",
    """    private var sessions: [UUID: PeerSession] = [:]\n    private var connectingPeerIDs: Set<String> = []\n    private var preferredSlotByPeerID: [String: Int] = [:]\n    private var desiredPeerIDs: Set<String> = []\n    private var reconnectAttempts: [String: Int] = [:]\n    private var reconnectTasks: [String: Task<Void, Never>] = [:]\n    private var participantRemovalTasks: [String: Task<Void, Never>] = [:]\n    private var diagnosticSessionID: UUID?\n""",
)

replace_once(
    iroh,
    """        let trimmed = normalizedEndpointID(rawEndpointId)\n        guard !trimmed.isEmpty, trimmed != endpointId else { return }\n        guard session(forPeerID: trimmed) == nil, !connectingPeerIDs.contains(trimmed) else { return }\n""",
    """        let trimmed = normalizedEndpointID(rawEndpointId)\n        guard !trimmed.isEmpty, trimmed != endpointId else { return }\n\n        // A peer remains part of the desired group across transient QUIC/session\n        // failures. This prevents adding a second person from visually and\n        // logically evicting an already-connected first person while the mesh\n        // is converging.\n        desiredPeerIDs.insert(trimmed)\n        participantRemovalTasks.removeValue(forKey: trimmed)?.cancel()\n\n        guard session(forPeerID: trimmed) == nil, !connectingPeerIDs.contains(trimmed) else { return }\n""",
)

replace_once(
    iroh,
    """            } catch {\n                self.connectingPeerIDs.remove(trimmed)\n                self.preferredSlotByPeerID.removeValue(forKey: trimmed)\n                self.lastError = error.localizedDescription\n                self.updateConnectionState()\n            }\n""",
    """            } catch {\n                self.connectingPeerIDs.remove(trimmed)\n                self.preferredSlotByPeerID.removeValue(forKey: trimmed)\n                self.lastError = self.connectedPeerCount == 0 ? error.localizedDescription : nil\n                self.updateConnectionState()\n                self.scheduleReconnect(to: trimmed)\n            }\n""",
)

replace_once(
    iroh,
    """        sessions.removeAll()\n        connectingPeerIDs.removeAll()\n        preferredSlotByPeerID.removeAll()\n\n        for session in currentSessions {\n""",
    """        sessions.removeAll()\n        connectingPeerIDs.removeAll()\n        preferredSlotByPeerID.removeAll()\n        desiredPeerIDs.removeAll()\n\n        for task in reconnectTasks.values {\n            task.cancel()\n        }\n        reconnectTasks.removeAll()\n        reconnectAttempts.removeAll()\n\n        for task in participantRemovalTasks.values {\n            task.cancel()\n        }\n        participantRemovalTasks.removeAll()\n\n        for session in currentSessions {\n""",
)

replace_once(
    iroh,
    """        session.peerID = remoteID\n        connectingPeerIDs.remove(remoteID)\n\n        let isExistingParticipant = remoteSlots.contains(where: { $0?.id == remoteID })\n""",
    """        session.peerID = remoteID\n        connectingPeerIDs.remove(remoteID)\n        desiredPeerIDs.insert(remoteID)\n        reconnectAttempts[remoteID] = 0\n        reconnectTasks.removeValue(forKey: remoteID)?.cancel()\n        participantRemovalTasks.removeValue(forKey: remoteID)?.cancel()\n\n        let isExistingParticipant = remoteSlots.contains(where: { $0?.id == remoteID })\n""",
)

replace_once(
    iroh,
    """    private func failSession(_ sessionID: UUID, error: Error) {\n        lastError = error.localizedDescription\n        removeSession(sessionID, clearParticipant: true)\n    }\n\n    private func removeSession(_ sessionID: UUID, clearParticipant: Bool) {\n""",
    """    private func failSession(_ sessionID: UUID, error: Error) {\n        let peerID = sessions[sessionID]?.peerID\n\n        // A failed edge is not the same thing as a participant leaving the\n        // Landline. Keep the participant in its dial slot while we repair the\n        // direct session. The previous behaviour immediately cleared the slot,\n        // which made an existing user appear to be replaced when a new mesh\n        // connection was being formed.\n        removeSession(sessionID, clearParticipant: false)\n        lastError = connectedPeerCount == 0 ? error.localizedDescription : nil\n\n        if let peerID {\n            scheduleReconnect(to: peerID)\n        }\n    }\n\n    private func scheduleReconnect(to rawPeerID: String) {\n        let peerID = normalizedEndpointID(rawPeerID)\n        guard endpointReady,\n              !peerID.isEmpty,\n              desiredPeerIDs.contains(peerID),\n              session(forPeerID: peerID) == nil,\n              !connectingPeerIDs.contains(peerID),\n              reconnectTasks[peerID] == nil\n        else { return }\n\n        let attempt = reconnectAttempts[peerID, default: 0]\n        guard attempt < 4 else {\n            scheduleParticipantRemoval(peerID)\n            return\n        }\n\n        reconnectAttempts[peerID] = attempt + 1\n        participantRemovalTasks.removeValue(forKey: peerID)?.cancel()\n        let delayMilliseconds = [300, 700, 1_500, 3_000][attempt]\n\n        reconnectTasks[peerID] = Task { @MainActor [weak self] in\n            try? await Task.sleep(for: .milliseconds(delayMilliseconds))\n            guard let self, !Task.isCancelled else { return }\n\n            self.reconnectTasks[peerID] = nil\n            guard self.endpointReady,\n                  self.desiredPeerIDs.contains(peerID),\n                  self.session(forPeerID: peerID) == nil,\n                  !self.connectingPeerIDs.contains(peerID)\n            else { return }\n\n            self.connect(to: peerID)\n        }\n    }\n\n    private func scheduleParticipantRemoval(_ peerID: String) {\n        guard participantRemovalTasks[peerID] == nil else { return }\n\n        participantRemovalTasks[peerID] = Task { @MainActor [weak self] in\n            // Give the direct mesh enough time to settle before declaring the\n            // peer gone. Four reconnect attempts already span roughly 5.5 s.\n            try? await Task.sleep(for: .seconds(5))\n            guard let self, !Task.isCancelled else { return }\n\n            self.participantRemovalTasks[peerID] = nil\n            guard self.session(forPeerID: peerID) == nil,\n                  !self.connectingPeerIDs.contains(peerID)\n            else { return }\n\n            self.desiredPeerIDs.remove(peerID)\n            self.reconnectAttempts.removeValue(forKey: peerID)\n            self.removeRemoteParticipant(peerID)\n\n            if self.remoteSpeakerID == peerID {\n                self.remoteSpeakerID = nil\n                self.remoteSpeakerName = nil\n                self.playback.reset()\n            }\n\n            self.updateConnectionState()\n            await self.broadcastMembership()\n        }\n    }\n\n    private func removeSession(_ sessionID: UUID, clearParticipant: Bool) {\n""",
)

replace_once(
    content,
    """    private func defaultAvatarImage() -> NSImage? {\n        NSImage(named: NSImage.Name(\"ToyBuddha\"))\n    }\n""",
    """    private func defaultAvatarImage() -> NSImage? {\n        guard let url = Bundle.main.url(forResource: \"avatar_toyface\", withExtension: \"png\") else {\n            return nil\n        }\n        return NSImage(contentsOf: url)\n    }\n""",
)

source_avatar = Path("prototypes/app/assets/avatar-toyface.png")
destination_avatar = Path("LandlineMac/Resources/avatar_toyface.png")
if not source_avatar.is_file():
    raise RuntimeError(f"Canonical default avatar is missing: {source_avatar}")
destination_avatar.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source_avatar, destination_avatar)

print("Applied macOS multi-user participant-retention and default-avatar repair")
