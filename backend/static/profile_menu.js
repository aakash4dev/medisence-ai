
// ========================================
// PROFILE MENU FUNCTIONS
// ========================================

function toggleProfileMenu() {
  const profileDropdown = document.getElementById("profileDropdown");

  // If user is authenticated, show profile menu
  if (AUTHENTICATED_USER) {
    if (profileDropdown.style.display === "none" || !profileDropdown.style.display) {
      openProfileMenu();
    } else {
      closeProfileMenu();
    }
  } else {
    // If not authenticated, show auth modal
    openAuthModal();
  }
}

function openProfileMenu() {
  const profileDropdown = document.getElementById("profileDropdown");
  if (profileDropdown) {
    // Update profile menu with latest user data
    updateProfileMenuData();

    profileDropdown.style.display = "block";
    console.log("✅ Profile menu opened");

    // Add click-outside listener
    setTimeout(() => {
      document.addEventListener("click", handleProfileMenuClickOutside);
    }, 100);
  }
}

function closeProfileMenu() {
  const profileDropdown = document.getElementById("profileDropdown");
  if (profileDropdown) {
    profileDropdown.style.display = "none";
    console.log("✅ Profile menu closed");

    // Remove click-outside listener
    document.removeEventListener("click", handleProfileMenuClickOutside);
  }
}

function handleProfileMenuClickOutside(event) {
  const profileContainer = document.querySelector(".profile-menu-container");

  // Check if click is outside the profile menu container
  if (profileContainer && !profileContainer.contains(event.target)) {
    closeProfileMenu();
  }
}

function updateProfileMenuData() {
  if (!AUTHENTICATED_USER) return;

  const profileAvatar = document.getElementById("profileAvatar");
  const profileName = document.getElementById("profileName");
  const profileEmail = document.getElementById("profileEmail");

  const name = AUTHENTICATED_USER.displayName || AUTHENTICATED_USER.email?.split('@')[0] || "User";
  const email = AUTHENTICATED_USER.email || "No email";
  const seed = AUTHENTICATED_USER.email || AUTHENTICATED_USER.uid || name;

  // Use the actual Google account photo; fall back to our SVG initial avatar if none.
  const avatarSrc = AUTHENTICATED_USER.photoURL ||
    (typeof buildAvatarSVG === 'function'
      ? buildAvatarSVG(name, seed)
      : `https://ui-avatars.com/api/?name=${encodeURIComponent(name.charAt(0))}&length=1&background=4285F4&color=fff&bold=true&size=128`);

  if (profileAvatar) {
    profileAvatar.src = avatarSrc;
    profileAvatar.alt = name;
    profileAvatar.style.display = 'block';
    profileAvatar.onerror = function() {
      // If Google photo fails to load, fall back to SVG
      this.onerror = null;
      this.src = typeof buildAvatarSVG === 'function'
        ? buildAvatarSVG(name, seed)
        : `https://ui-avatars.com/api/?name=${encodeURIComponent(name.charAt(0))}&length=1&background=4285F4&color=fff&bold=true&size=128`;
    };
  }
  if (profileName) {
    profileName.textContent = name;
  }
  if (profileEmail) {
    profileEmail.textContent = email;
  }
}

async function handleSignOut() {
  console.log("🔓 Sign out initiated from profile menu");

  // Close profile menu first
  closeProfileMenu();

  // Show loading toast
  showToast("Signing out...", "info");

  try {
    if (window.firebaseAuth) {
      await window.firebaseAuth.signOut(window.firebaseAuth.auth);
    }

    // CLEAR ALL STATE - CRITICAL FOR SECURITY
    clearAuthState();
    state.currentUser = null;
    state.chatHistory = [];
    state.appointments = [];
    state.symptoms = [];
    state.currentImage = null;

    // CLEAR LOCAL STORAGE
    localStorage.removeItem("medicsense_user_id");
    localStorage.removeItem("medicsense_chat_history");
    localStorage.removeItem("medicsense_appointments");
    localStorage.removeItem("medicsense_symptoms");

    // CLEAR CHAT UI
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages) {
      chatMessages.innerHTML = `
        <div class="message ai-message">
          <div class="message-avatar">
            <i class="fas fa-robot"></i>
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <p><strong>👋 Welcome back!</strong></p>
              <p>How can I help you today?</p>
            </div>
            <div class="message-meta">
              <span class="message-time">Just now</span>
            </div>
          </div>
        </div>
      `;
    }

    await new Promise((r) => setTimeout(r, 500));

    showToast("Successfully signed out", "success");
    console.log("✅ Sign out successful");
  } catch (error) {
    console.error("❌ LOGOUT ERROR", error);
    showToast("Error signing out: " + error.message, "error");
  }
}
