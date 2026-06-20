// ========================================
// AUTH STATE MANAGEMENT - FIREBASE ONLY
// ========================================

// Backend sync - called ONLY after Firebase auth succeeds
async function syncWithBackend(firebaseUser, idToken) {
  try {
    console.log("📡 Syncing with backend...");
    const apiBaseUrl = (window.ENV && window.ENV.API_BASE_URL) || 'http://localhost:5000/api';
    const response = await fetch(`${apiBaseUrl}/auth/google`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        name: firebaseUser.displayName,
        photo: firebaseUser.photoURL,
        provider: "google",
        idToken: idToken
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();

    if (data.success && data.token) {
      localStorage.setItem("medicsense_backend_token", data.token);
      console.log("✅ Backend sync successful");
      return true;
    } else {
      throw new Error(data.message || "Backend sync failed");
    }
  } catch (error) {
    console.error("❌ Backend sync failed:", error);
    // CRITICAL: Sign out from Firebase on backend failure
    if (window.firebaseAuth) {
      await window.firebaseAuth.signOut(window.firebaseAuth.auth);
    }
    localStorage.removeItem("medicsense_backend_token");
    throw error;
  }
}

// Clear all auth state
function clearAuthState() {
  AUTHENTICATED_USER = null;
  localStorage.removeItem("medicsense_backend_token");
  localStorage.removeItem("medicsense_user_id");
  console.log("✅ Auth state cleared");
}

// Setup Firebase auth listener - SINGLE SOURCE OF TRUTH
function setupAuthListener() {
  if (!window.firebaseAuth) {
    console.error("❌ Firebase auth not available");
    return;
  }

  const { auth, onAuthStateChanged } = window.firebaseAuth;

  console.log("🔐 Setting up auth state listener...");

  // SINGLE SOURCE OF TRUTH: Firebase onAuthStateChanged
  onAuthStateChanged(auth, async (user) => {
    console.log(
      "🔐 Auth state changed:",
      user ? `Logged in as ${user.email || user.uid}` : "Logged out"
    );

    if (user) {
      // User is authenticated in Firebase
      console.log("✅ Firebase user authenticated:", {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
      });

      // Set global auth state
      AUTHENTICATED_USER = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
      };
      state.currentUser = user.uid;

      // Get ID token and sync with backend
      try {
        const idToken = await user.getIdToken();
        await syncWithBackend(user, idToken);

        // Update UI after successful backend sync
        updateAuthUI(user);

        // Close auth modal if open
        const modal = document.getElementById("authModal");
        if (modal && modal.style.display === "flex") {
          closeAuthModal();
          setTimeout(() => {
            showToast(
              `Welcome back, ${user.displayName || user.email || "User"}!`,
              "success"
            );
          }, 300);
        }

        // Load notifications
        loadNotificationCountSafe().catch((err) => {
          console.warn("⚠️ Failed to load notifications:", err);
        });
      } catch (error) {
        console.error("❌ Backend sync failed, user signed out:", error);
        showToast("Authentication failed. Please try again.", "error");
        // User will be signed out by syncWithBackend
      }
    } else {
      // User is logged out
      console.log("ℹ️ User logged out");

      // Clear all state
      clearAuthState();
      state.currentUser = null;
      updateAuthUI(null);

      // Reset UI to login state
      restoreAuthModal();
    }

    // Reset loading state
    setAuthLoading(false);
  });
}
