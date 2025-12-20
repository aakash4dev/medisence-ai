import { auth, googleProvider, signInWithPopup, signOut, onAuthStateChanged } from './firebase_config.js';

// UI Elements
const authBtn = document.getElementById('authBtn');
const authModal = document.getElementById('authModal');

// Open/Close Modal
window.openAuthModal = () => {
    if (auth.currentUser) {
        // If logged in, redirect to profile page
        window.location.href = 'profile.html';
    } else {
        // If not logged in, redirect to auth page
        window.location.href = 'auth.html';
    }
};

window.closeAuthModal = () => {
    if (authModal) authModal.style.display = 'none';
};

// Google Login
window.handleGoogleLogin = async () => {
    try {
        const result = await signInWithPopup(auth, googleProvider);
        const user = result.user;
        console.log("User logged in:", user);
        showToast(`Welcome back, ${user.displayName}!`, "success");
        closeAuthModal();
    } catch (error) {
        console.error("Login failed:", error);
        showToast("Login failed: " + error.message, "error");
    }
};

// Email Login (Placeholder/Stub for now as per minimal request, but structure is there)
window.handleEmailLogin = (e) => {
    e.preventDefault();
    showToast("Email login not fully configured yet. Please use Google.", "info");
};

// Logout
const handleLogout = async () => {
    try {
        await signOut(auth);
        showToast("Logged out successfully", "info");
    } catch (error) {
        console.error("Logout error:", error);
    }
};

// Auth State Observer
onAuthStateChanged(auth, (user) => {
    if (user) {
        // User is signed in
        if (authBtn) {
            authBtn.innerHTML = `<img src="${user.photoURL}" style="width: 24px; height: 24px; border-radius: 50%;">`;
            authBtn.title = `Logged in as ${user.displayName}`;
        }
    } else {
        // User is signed out
        if (authBtn) {
            authBtn.innerHTML = `<i class="fas fa-user-circle"></i>`;
            authBtn.title = "Login";
        }
    }
});

// Helper for Toast (reusing existing one from script_ultra.js if available, else simple alert)
function showToast(msg, type) {
    if (window.showToast) {
        window.showToast(msg, type);
    } else {
        alert(msg);
    }
}
