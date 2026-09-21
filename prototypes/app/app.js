(() => {
  const ASSET_BASE = 'assets';
  const PINNED_BASE = 'https://raw.githubusercontent.com/mattatgit/landline/6f57d9f20c88eb568b3cf24d0264bf826f8918e7/prototypes/app/assets';
  const TOYFACE_REMOTE = ASSET_BASE + '/avatar-saori.png';

  const landline = document.getElementById('landline');
  const groupTitle = document.getElementById('group-title');
  const groupTitleCopy = document.getElementById('group-title-copy');
  const groupTitleIcon = document.getElementById('group-title-icon');
  const groupDropdown = document.getElementById('group-dropdown');
  const selfContact = document.getElementById('self-contact');
  const selfAvatar = document.getElementById('self-avatar');
  const remoteSlots = [2,3,4,5,6,7,8].map((n) => document.querySelector('.pos-' + n));
  const overlays = [...document.querySelectorAll('.sheet-overlay')];

  const groups = {
    home: { label: 'Home dial', cls: 'home', self: TOYFACE_REMOTE },
    'saori-matt': { label: 'Saori, Matt', cls: 'apricot', self: ASSET_BASE + '/avatar-saori.png' },
    work: { label: 'Work people', cls: 'pink', self: ASSET_BASE + '/avatar-saori.png' },
    family: { label: 'Family chat', cls: 'blue', self: ASSET_BASE + '/avatar-saori.png' }
  };

  let currentGroup = 'home';
  let selectedAddSlot = null;
  let selectedMember = null;
  let profileImageData = null;
  let groupImageData = null;

  const resetSlot = (slot, n) => {
    slot.className = 'contact empty add-slot pos-' + n;
    slot.type = 'button';
    slot.dataset.slot = String(n);
    slot.setAttribute('aria-label', 'Add someone to Landline');
    slot.title = '';
    slot.innerHTML = '<img class="empty-hover-art" src="' + ASSET_BASE + '/hovered-slot.svg" alt="">';
  };

  const closeDropdown = () => {
    groupDropdown.classList.remove('is-open');
    groupDropdown.setAttribute('aria-hidden', 'true');
    groupTitle.setAttribute('aria-expanded', 'false');
  };

  let sheetSizeTimer = 0;
  const clearSheetSizing = (sheet) => {
    if (!sheet) return;
    sheet.classList.remove('sheet-size-motion');
    sheet.style.height = '';
  };

  const closeAllSheets = () => {
    window.clearTimeout(sheetSizeTimer);
    sheetSizeTimer = 0;
    overlays.forEach((overlay) => {
      overlay.classList.remove('is-open', 'no-enter-motion');
      overlay.setAttribute('aria-hidden', 'true');
      clearSheetSizing(overlay.querySelector('.bottom-sheet'));
    });
  };

  const openSheet = (id) => {
    closeDropdown();
    const currentOverlay = overlays.find((overlay) => overlay.classList.contains('is-open'));
    const switchingBetweenSheets = Boolean(currentOverlay && currentOverlay.id !== id);
    const sourceSheet = currentOverlay && currentOverlay.querySelector('.bottom-sheet');
    const sourceHeight = sourceSheet ? sourceSheet.getBoundingClientRect().height : 0;

    window.clearTimeout(sheetSizeTimer);
    overlays.forEach((item) => {
      item.classList.remove('is-open', 'no-enter-motion');
      item.setAttribute('aria-hidden', 'true');
      clearSheetSizing(item.querySelector('.bottom-sheet'));
    });

    const overlay = document.getElementById(id);
    if (!overlay) return;
    const targetSheet = overlay.querySelector('.bottom-sheet');
    const targetHeight = targetSheet && targetSheet.classList.contains('sheet-240') ? 240 : 584;
    const sizeChanges = switchingBetweenSheets && sourceHeight && Math.abs(sourceHeight - targetHeight) > 1;

    if (switchingBetweenSheets) overlay.classList.add('no-enter-motion');
    if (sizeChanges && targetSheet) {
      targetSheet.style.height = sourceHeight + 'px';
      targetSheet.classList.add('sheet-size-motion');
    }

    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');

    if (switchingBetweenSheets) {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          if (sizeChanges && targetSheet) {
            targetSheet.style.height = targetHeight + 'px';
            sheetSizeTimer = window.setTimeout(() => {
              clearSheetSizing(targetSheet);
              overlay.classList.remove('no-enter-motion');
              sheetSizeTimer = 0;
            }, 180);
          } else {
            overlay.classList.remove('no-enter-motion');
          }
        });
      });
    }
  };

  const populateRemoteSlot = (slotIndex, name, assetName) => {
    const slot = remoteSlots[slotIndex];
    const position = slotIndex + 2;
    slot.className = 'contact online pos-' + position;
    slot.removeAttribute('data-slot');
    slot.setAttribute('aria-label', name);
    slot.title = name;
    slot.innerHTML = '<img src="' + ASSET_BASE + '/' + assetName + '" alt="' + name + '">';
  };

  const renderGroup = (key) => {
    const group = groups[key] || groups.home;
    currentGroup = key;
    groupTitleCopy.textContent = group.label;
    groupTitleIcon.className = 'group-mini ' + group.cls;
    selfAvatar.src = group.self;
    selfAvatar.onerror = () => {
      selfAvatar.onerror = null;
      selfAvatar.src = ASSET_BASE + '/avatar-saori.png';
    };
    remoteSlots.forEach((slot, index) => resetSlot(slot, index + 2));

    if (key === 'saori-matt') {
      populateRemoteSlot(0, 'Matt', 'avatar-micheal.png');
    } else if (key === 'work') {
      populateRemoteSlot(0, 'Fiona', 'avatar-fiona.png');
      populateRemoteSlot(1, 'Stuart', 'avatar-stuart.png');
      populateRemoteSlot(2, 'Matt', 'avatar-micheal.png');
    } else if (key === 'family') {
      populateRemoteSlot(0, 'Yumie', 'avatar-yumie.png');
      populateRemoteSlot(1, 'Michiyo', 'avatar-michiyo.png');
    }

    bindAddSlots();
    closeDropdown();
    closeAllSheets();
  };

  groupTitle.addEventListener('click', (event) => {
    event.stopPropagation();
    const open = !groupDropdown.classList.contains('is-open');
    groupDropdown.classList.toggle('is-open', open);
    groupDropdown.setAttribute('aria-hidden', String(!open));
    groupTitle.setAttribute('aria-expanded', String(open));
  });
  groupDropdown.querySelectorAll('[data-group]').forEach((button) => {
    button.addEventListener('click', () => renderGroup(button.dataset.group));
  });
  window.addEventListener('click', (event) => {
    if (!groupDropdown.contains(event.target) && !groupTitle.contains(event.target)) closeDropdown();
  });

  // Share your ID: click the local avatar.
  const openShare = () => openSheet('share-overlay');
  selfContact.addEventListener('click', openShare);
  selfContact.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openShare(); }
  });

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const helper = document.createElement('textarea');
    helper.value = text;
    helper.setAttribute('readonly', '');
    helper.style.position = 'fixed';
    helper.style.opacity = '0';
    document.body.appendChild(helper);
    helper.select();
    document.execCommand('copy');
    helper.remove();
  };
  document.getElementById('copy-share-id').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    try { await copyText(document.getElementById('share-landline-id').textContent.trim()); } catch (_) {}
    button.textContent = 'Copied';
    window.setTimeout(() => { button.textContent = 'Copy ID'; }, 900);
  });

  // Saori's Landline menu replaces the old direct Dial groups action.
  document.getElementById('dial-groups-button').addEventListener('click', () => openSheet('landline-menu-overlay'));
  document.getElementById('edit-profile-row').addEventListener('click', () => openSheet('edit-profile-overlay'));
  document.getElementById('groups-row').addEventListener('click', () => openSheet('group-overlay'));
  document.getElementById('edit-profile-arrow').addEventListener('click', () => openSheet('landline-menu-overlay'));
  document.getElementById('dial-groups-arrow').addEventListener('click', () => openSheet('landline-menu-overlay'));

  let createGroupExternalAdded = false;
  const createGroupSelectButtons = [...document.querySelectorAll('.group-member-select')];
  const createGroupNext = document.getElementById('create-group-next');
  const createGroupIdInput = document.getElementById('create-group-landline-id');
  const updateCreateGroupNext = () => {
    const anySelected = createGroupExternalAdded || createGroupSelectButtons.some((button) => button.getAttribute('aria-pressed') === 'true');
    createGroupNext.disabled = !anySelected;
  };
  const resetCreateGroupSelection = () => {
    createGroupExternalAdded = false;
    createGroupIdInput.value = '';
    createGroupSelectButtons.forEach((button) => button.setAttribute('aria-pressed', 'false'));
    updateCreateGroupNext();
  };
  document.getElementById('create-new-group').addEventListener('click', () => {
    resetCreateGroupSelection();
    openSheet('create-group-overlay');
  });
  document.getElementById('create-group-arrow').addEventListener('click', () => openSheet('group-overlay'));
  createGroupSelectButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const selected = button.getAttribute('aria-pressed') === 'true';
      button.setAttribute('aria-pressed', String(!selected));
      updateCreateGroupNext();
    });
  });
  document.getElementById('create-group-enter-id').addEventListener('click', () => {
    openSheet('create-group-id-overlay');
    window.setTimeout(() => createGroupIdInput.focus(), 120);
  });
  document.getElementById('create-group-id-arrow').addEventListener('click', () => openSheet('create-group-overlay'));
  const addCreateGroupId = () => {
    if (!createGroupIdInput.value.trim()) return;
    createGroupExternalAdded = true;
    updateCreateGroupNext();
    openSheet('create-group-overlay');
  };
  document.getElementById('create-group-id-add').addEventListener('click', addCreateGroupId);
  createGroupIdInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); addCreateGroupId(); }
  });
  createGroupNext.addEventListener('click', () => {
    if (createGroupNext.disabled) return;
    openSheet('group-profile-overlay');
    window.setTimeout(() => document.getElementById('group-name-input').focus(), 120);
  });
  document.getElementById('group-profile-arrow').addEventListener('click', () => openSheet('create-group-overlay'));

  const groupPageOverlayByKey = {
    'saori-matt': 'group-page-overlay',
    work: 'work-group-page-overlay',
    family: 'family-group-page-overlay'
  };
  const groupEditClassByKey = {
    'saori-matt': '',
    work: 'work',
    family: 'family'
  };
  let activeGroupPageKey = 'saori-matt';
  let groupEditInitialName = 'Matt & Saori';

  const openGroupPage = (key) => {
    if (!groupPageOverlayByKey[key]) return;
    activeGroupPageKey = key;
    openSheet(groupPageOverlayByKey[key]);
  };

  document.getElementById('saori-matt-group-row').addEventListener('click', () => openGroupPage('saori-matt'));
  document.querySelectorAll('[data-group-page]').forEach((button) => {
    button.addEventListener('click', () => openGroupPage(button.dataset.groupPage));
  });
  document.querySelectorAll('.group-page-back').forEach((button) => {
    button.addEventListener('click', () => openSheet('group-overlay'));
  });
  document.querySelectorAll('[data-start-group]').forEach((button) => {
    button.addEventListener('click', () => renderGroup(button.dataset.startGroup));
  });

  // New Add someone -> Enter a Landline ID split flow.
  const addOverlay = document.getElementById('add-overlay');
  const enterIdInput = document.getElementById('landline-id-input');
  const memberRows = [...document.querySelectorAll('.member-row')];

  const resetMemberSelection = () => {
    selectedMember = null;
    memberRows.forEach((row) => row.classList.remove('is-selected'));
  };
  const openAddSheet = (slot) => {
    selectedAddSlot = slot;
    resetMemberSelection();
    enterIdInput.value = '';
    openSheet('add-overlay');
  };
  const closeAddFlow = () => {
    selectedAddSlot = null;
    resetMemberSelection();
    enterIdInput.value = '';
    closeAllSheets();
  };
  function bindAddSlots() {
    document.querySelectorAll('.add-slot').forEach((slot) => {
      slot.onclick = () => openAddSheet(slot);
    });
  }
  memberRows.forEach((row) => {
    row.addEventListener('click', () => {
      memberRows.forEach((other) => other.classList.remove('is-selected'));
      row.classList.add('is-selected');
      selectedMember = { name: row.dataset.member, avatar: row.dataset.avatar };
    });
  });
  document.getElementById('enter-id-row').addEventListener('click', () => {
    openSheet('enter-id-overlay');
    window.setTimeout(() => enterIdInput.focus(), 120);
  });
  document.getElementById('enter-id-arrow').addEventListener('click', () => openSheet('add-overlay'));

  const populateSelectedSlot = (name, avatar) => {
    if (!selectedAddSlot) return false;
    const slot = selectedAddSlot;
    slot.className = slot.className.replace('empty add-slot', 'online added-user');
    slot.removeAttribute('data-slot');
    slot.setAttribute('aria-label', name);
    slot.title = name;
    slot.innerHTML = '<img src="' + avatar + '" onerror="this.onerror=null;this.src=\'' + ASSET_BASE + '/avatar-saori.png\'" alt="' + name.replace(/"/g, '') + '">';
    selectedAddSlot = null;
    closeAllSheets();
    return true;
  };

  document.getElementById('add-existing-person').addEventListener('click', () => {
    if (!selectedMember) return;
    populateSelectedSlot(selectedMember.name, selectedMember.avatar);
    resetMemberSelection();
  });
  const addEnteredId = () => {
    const id = enterIdInput.value.trim();
    if (!id) return;
    populateSelectedSlot(id, TOYFACE_REMOTE);
    enterIdInput.value = '';
  };
  document.getElementById('enter-id-add').addEventListener('click', addEnteredId);
  enterIdInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); addEnteredId(); }
  });
  document.querySelectorAll('[data-close-add]').forEach((button) => button.addEventListener('click', closeAddFlow));

  // Edit profile upload / drop / update.
  const profileNameInput = document.getElementById('profile-name-input');
  const profileAvatarUpload = document.getElementById('profile-avatar-upload');
  const profileAvatarFile = document.getElementById('profile-avatar-file');
  const profileAvatarPreview = document.getElementById('profile-avatar-preview');
  const groupAvatarUpload = document.getElementById('group-avatar-upload');
  const groupAvatarFile = document.getElementById('group-avatar-file');
  const groupAvatarPreview = document.getElementById('group-avatar-preview');
  const groupEditNameInput = document.getElementById('group-edit-name-input');
  const groupEditAvatarUpload = document.getElementById('group-edit-avatar-upload');
  const groupEditAvatarFile = document.getElementById('group-edit-avatar-file');
  const groupEditAvatarPreview = document.getElementById('group-edit-avatar-preview');
  const groupEditSave = document.getElementById('group-edit-save');
  const groupEditAvatarCircle = document.getElementById('group-edit-avatar-circle');
  let groupEditImageData = null;

  const openGroupEdit = (key) => {
    activeGroupPageKey = key;
    const pageName = document.querySelector('[data-group-page-name="' + key + '"]');
    groupEditInitialName = pageName ? pageName.textContent.trim() : (groups[key] ? groups[key].label : 'Dial group');
    groupEditNameInput.value = groupEditInitialName;
    groupEditImageData = null;
    groupEditAvatarPreview.hidden = true;
    groupEditAvatarPreview.removeAttribute('src');
    groupEditAvatarCircle.className = 'group-edit-avatar-circle' + (groupEditClassByKey[key] ? ' ' + groupEditClassByKey[key] : '');
    groupEditSave.disabled = true;
    openSheet('group-profile-edit-overlay');
  };

  document.querySelectorAll('[data-edit-group]').forEach((button) => {
    button.addEventListener('click', () => openGroupEdit(button.dataset.editGroup));
  });
  document.getElementById('group-edit-arrow').addEventListener('click', () => openGroupPage(activeGroupPageKey));

  const readImage = (file, onReady) => {
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => onReady(String(reader.result || ''));
    reader.readAsDataURL(file);
  };
  const bindUpload = (button, input, onReady) => {
    button.addEventListener('click', () => input.click());
    input.addEventListener('change', () => readImage(input.files && input.files[0], onReady));
    ['dragenter','dragover'].forEach((name) => button.addEventListener(name, (event) => {
      event.preventDefault(); button.classList.add('dragging');
    }));
    ['dragleave','drop'].forEach((name) => button.addEventListener(name, (event) => {
      event.preventDefault(); button.classList.remove('dragging');
    }));
    button.addEventListener('drop', (event) => readImage(event.dataTransfer && event.dataTransfer.files[0], onReady));
  };
  bindUpload(profileAvatarUpload, profileAvatarFile, (data) => {
    profileImageData = data;
    profileAvatarPreview.src = data;
  });
  bindUpload(groupAvatarUpload, groupAvatarFile, (data) => {
    groupImageData = data;
    groupAvatarPreview.src = data;
    groupAvatarPreview.hidden = false;
  });
  bindUpload(groupEditAvatarUpload, groupEditAvatarFile, (data) => {
    groupEditImageData = data;
    groupEditAvatarPreview.src = data;
    groupEditAvatarPreview.hidden = false;
    groupEditSave.disabled = false;
  });
  groupEditNameInput.addEventListener('input', () => {
    groupEditSave.disabled = groupEditNameInput.value.trim() === groupEditInitialName && !groupEditImageData;
  });
  groupEditSave.addEventListener('click', () => {
    if (groupEditSave.disabled) return;
    const nextName = groupEditNameInput.value.trim() || groupEditInitialName;
    const pageName = document.querySelector('[data-group-page-name="' + activeGroupPageKey + '"]');
    if (pageName) pageName.textContent = nextName;
    if (groups[activeGroupPageKey]) groups[activeGroupPageKey].label = nextName;
    groupEditInitialName = nextName;
    groupEditSave.disabled = true;
    openGroupPage(activeGroupPageKey);
  });
  document.getElementById('profile-update').addEventListener('click', () => {
    if (profileImageData) {
      selfAvatar.src = profileImageData;
      if (currentGroup === 'home') groups.home.self = profileImageData;
    }
    closeAllSheets();
  });

  // Create group profile completes the prototype by returning to the dial with the new group title.
  document.getElementById('group-create').addEventListener('click', () => {
    const name = document.getElementById('group-name-input').value.trim() || 'New group';
    groupTitleCopy.textContent = name;
    groupTitleIcon.className = 'group-mini apricot';
    if (groupImageData) {
      groupTitleIcon.style.backgroundImage = 'url("' + groupImageData + '")';
      groupTitleIcon.style.backgroundSize = 'cover';
      groupTitleIcon.style.backgroundPosition = 'center';
    } else {
      groupTitleIcon.style.backgroundImage = '';
    }
    closeAllSheets();
  });

  document.querySelectorAll('[data-close-sheet]').forEach((button) => button.addEventListener('click', closeAllSheets));

  // V22 volume behavior retained.
  const slider = document.getElementById('volume-slider');
  const valueLabel = document.getElementById('volume-value');
  let volume = Number(slider.getAttribute('aria-valuenow')) || 25;
  let dragging = false;
  const setVolume = (nextValue) => {
    volume = Math.max(0, Math.min(100, Math.round(nextValue)));
    slider.style.setProperty('--volume', volume);
    slider.setAttribute('aria-valuenow', String(volume));
    valueLabel.value = String(volume);
    valueLabel.textContent = String(volume);
  };
  const setFromPointer = (event) => {
    const rect = slider.getBoundingClientRect();
    setVolume(((event.clientX - rect.left) / rect.width) * 100);
  };
  slider.addEventListener('pointerdown', (event) => {
    dragging = true; slider.setPointerCapture(event.pointerId); setFromPointer(event);
  });
  slider.addEventListener('pointermove', (event) => { if (dragging) setFromPointer(event); });
  slider.addEventListener('pointerup', (event) => {
    dragging = false; if (slider.hasPointerCapture(event.pointerId)) slider.releasePointerCapture(event.pointerId);
  });
  slider.addEventListener('pointercancel', () => { dragging = false; });
  slider.addEventListener('keydown', (event) => {
    const step = event.shiftKey ? 5 : 1;
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') { event.preventDefault(); setVolume(volume + step); }
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') { event.preventDefault(); setVolume(volume - step); }
    else if (event.key === 'Home') { event.preventDefault(); setVolume(0); }
    else if (event.key === 'End') { event.preventDefault(); setVolume(100); }
  });

  // V22 PTT/VU behavior retained.
  const ptt = document.getElementById('ptt');
  const vuBars = [...document.querySelectorAll('#vu-bars span')];
  let vuTimer = null;
  let vuIndex = 0;
  const vuPattern = [5,7,6,9,8,10,7,11,8,12,9,13,8,10,15,9,7,11];
  const vuColors = ['#17b239','#ff9601','#ff6157'];
  const paintVu = (level) => {
    vuBars.forEach((bar, index) => {
      bar.style.background = index >= level ? '#777f78' : index < 10 ? vuColors[0] : index < 13 ? vuColors[1] : vuColors[2];
    });
  };
  const stopVu = () => {
    if (vuTimer) window.clearInterval(vuTimer);
    vuTimer = null; paintVu(0);
  };
  const startVu = () => {
    stopVu(); vuIndex = 0; paintVu(vuPattern[0]);
    vuTimer = window.setInterval(() => { vuIndex = (vuIndex + 1) % vuPattern.length; paintVu(vuPattern[vuIndex]); }, 115);
  };
  ptt.addEventListener('pointerdown', startVu);
  window.addEventListener('pointerup', stopVu);
  window.addEventListener('pointercancel', stopVu);
  stopVu();

  bindAddSlots();
  window.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeDropdown();
    closeAddFlow();
    closeAllSheets();
  });
})();
