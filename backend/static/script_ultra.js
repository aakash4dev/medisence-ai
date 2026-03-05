/**
 * MedicSense AI - Ultra Professional Frontend JavaScript
 * Problem Statement Solution
 * Best-in-Class Functionality
 */

// ========================================
// CONFIGURATION
// ========================================
// Load configuration from environment variables
const getConfig = () => {
  // Try to get from window.ENV (loaded by env-loader.js)
  if (window.ENV) {
    return {
      API_BASE_URL: window.ENV.API_BASE_URL || "http://localhost:5000/api",
      USER_ID: "user_" + Math.random().toString(36).substr(2, 9),
      AI_ENABLED:
        window.ENV.APP?.AI_ENABLED !== undefined
          ? window.ENV.APP.AI_ENABLED
          : true,
      MAX_FILE_SIZE: window.ENV.APP?.MAX_FILE_SIZE || 10 * 1024 * 1024, // 10MB
      SUPPORTED_FORMATS: window.ENV.APP?.SUPPORTED_FORMATS || [
        "image/jpeg",
        "image/png",
        "image/webp",
      ],
    };
  }

  // Fallback to default values
  return {
    API_BASE_URL: "http://localhost:5000/api",
    USER_ID: "user_" + Math.random().toString(36).substr(2, 9),
    AI_ENABLED: true,
    MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
    SUPPORTED_FORMATS: ["image/jpeg", "image/png", "image/webp"],
  };
};

const CONFIG = getConfig();

// ========================================
// UTILITY: FETCH WITH TIMEOUT
// ========================================
/**
 * Fetch with automatic timeout to prevent hanging requests
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @param {number} timeoutMs - Timeout in milliseconds (default: 10000)
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      throw new Error(
        "Request timed out. Please check your connection and try again."
      );
    }
    throw error;
  }
}

// ========================================
// STATE MANAGEMENT
// ========================================
// SINGLE SOURCE OF TRUTH FOR AUTH STATE
let AUTHENTICATED_USER = null;
let AUTH_MODAL_CLOSED_BY_LOGIN = false; // Flag to prevent reopening after successful login

/**
 * ASYNC PROCESS LOCKS
 * Prevents race conditions and inconsistent UI states
 */
let isAnalyzing = false;

const state = {
  currentUser: null, // Will be set by Firebase auth
  chatHistory: [],
  currentImage: null,
  appointments: [],
  symptoms: [],
  isTyping: false,
  isMobileMenuOpen: false,
};

// ========================================
// INITIALIZATION - PRODUCTION GRADE
// ========================================

// Centralized loader control - SINGLE SOURCE OF TRUTH
const LoaderManager = {
  hidden: false,

  hide() {
    if (this.hidden) return; // Prevent multiple calls

    console.log("🕒 Hiding loader...");
    const loader = document.getElementById("loadingScreen");
    if (loader) {
      loader.style.opacity = "0";
      loader.style.transition = "opacity 0.3s ease-out";
      setTimeout(() => {
        loader.style.display = "none";
        this.hidden = true;
        console.log("✅ Loader hidden");
      }, 300);
    }

    // Clear safety watchdog
    if (window.clearLoaderSafety) {
      window.clearLoaderSafety();
    }
  },

  showError(message) {
    const loader = document.getElementById("loadingScreen");
    if (loader && !this.hidden) {
      const subtext = loader.querySelector(".loading-subtext");
      if (subtext) {
        subtext.textContent = message;
        subtext.style.color = "#ef4444";
      }
    }
  },
};

// ========================================
// AUTH STATE MANAGEMENT - PRODUCTION READY
// ========================================

// Check if user should see auth modal
function shouldShowAuthModal() {
  return !AUTHENTICATED_USER;
}

// Restore user from localStorage on page load
function restoreAuthState() {
  const savedUser = localStorage.getItem("medicsense_authenticated_user");
  const savedToken = localStorage.getItem("medicsense_auth_token");

  if (savedUser && savedToken) {
    try {
      AUTHENTICATED_USER = JSON.parse(savedUser);
      console.log(
        "✅ Auth state restored from localStorage:",
        AUTHENTICATED_USER.email || AUTHENTICATED_USER.uid
      );
      return true;
    } catch (error) {
      console.warn("⚠️ Could not restore auth state:", error);
      localStorage.removeItem("medicsense_authenticated_user");
      localStorage.removeItem("medicsense_auth_token");
    }
  }
  return false;
}

// Save authenticated user state
async function saveAuthState(user, token) {
  AUTHENTICATED_USER = {
    uid: user.uid,
    email: user.email,
    displayName: user.displayName,
    photoURL: user.photoURL,
    phoneNumber: user.phoneNumber,
  };

  localStorage.setItem(
    "medicsense_authenticated_user",
    JSON.stringify(AUTHENTICATED_USER)
  );
  if (token) {
    localStorage.setItem("medicsense_auth_token", token);
  }

  console.log("✅ Auth state saved to localStorage");

  // Register with backend
  if (token) {
    try {
      console.log("📡 Registering with backend...");
      const response = await fetch("http://localhost:5000/api/auth/google", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          idToken: token,
          user: {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
          },
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log("✅ Backend registration successful");
        // Save backend token if provided
        if (data.token) {
          localStorage.setItem("medicsense_backend_token", data.token);
        }
      } else {
        console.error("❌ Backend registration failed:", data.message);
      }
    } catch (error) {
      console.error("❌ Failed to register with backend:", error);
    }
  }
}

// Clear authenticated user state
function clearAuthState() {
  AUTHENTICATED_USER = null;
  AUTH_MODAL_CLOSED_BY_LOGIN = false; // Reset flag on logout
  localStorage.removeItem("medicsense_authenticated_user");
  localStorage.removeItem("medicsense_auth_token");
  console.log("✅ Auth state cleared");
}

// Critical initialization that MUST complete
async function initializeCriticalSystems() {
  console.log("🏥 MedicSense AI - Starting critical initialization");

  try {
    // 1. Restore auth state from localStorage FIRST
    restoreAuthState();

    // 2. Core synchronous initialization
    initializeAppCore();
    // NOTE: Event delegation is intentional.
    // Profile button is rendered dynamically after auth.
    // setupEventListeners(); // Function not defined - commented out
    updateSeverityDisplay();
    initAuthModal();

    console.log("✅ Core systems initialized");
    return true;
  } catch (error) {
    console.error("🔥 CRITICAL: Core initialization failed", error);
    LoaderManager.showError("Initialization failed. Retrying...");
    return false;
  }
}

// Optional async services that can fail gracefully
async function initializeOptionalSystems() {
  console.log("🔧 Loading optional systems...");

  // Auth system (can fail gracefully)
  try {
    await initializeAuthWithTimeout(5000); // 5 second timeout
    console.log("✅ Auth system ready");
  } catch (error) {
    console.warn("⚠️ Auth system failed to load:", error);
    console.warn("⚠️ App will continue in guest mode");
  }

  // Notifications (optional, non-blocking)
  try {
    await loadNotificationCountSafe();
    console.log("✅ Notifications loaded");
  } catch (error) {
    console.warn("⚠️ Notifications unavailable:", error);
  }
}

// Main initialization orchestrator
document.addEventListener("DOMContentLoaded", async function () {
  console.log("🚀 DOM Ready - Starting initialization sequence");

  try {
    // Phase 1: Critical systems (MUST succeed)
    const criticalSuccess = await initializeCriticalSystems();

    if (!criticalSuccess) {
      throw new Error("Critical systems failed");
    }

    // Phase 2: Hide loader immediately after critical systems ready
    // Don't wait for optional services
    LoaderManager.hide();

    // Phase 3: Load optional systems in background (non-blocking)
    initializeOptionalSystems().catch((err) => {
      console.warn("⚠️ Some optional services failed:", err);
    });

    console.log("✅ App initialized successfully");

    // Handle URL hash for scroll position (e.g., #appointments)
    if (window.location.hash) {
      setTimeout(() => {
        const hash = window.location.hash.substring(1);
        const element = document.getElementById(hash);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 500); // Small delay to ensure content is loaded
    }
  } catch (error) {
    console.error("🔥 FATAL: App initialization failed", error);

    // Force hide loader and show error
    LoaderManager.hide();

    // Show user-visible error
    setTimeout(() => {
      if (typeof showToast === "function") {
        showToast(
          "App loaded with limited functionality. Some features may be unavailable.",
          "warning"
        );
      } else {
        alert(
          "App loaded with limited functionality. Please refresh if issues persist."
        );
      }
    }, 500);
  }
});

// ========================================
// EVENT DELEGATION - PROFILE BUTTON
// ========================================
// Production-grade event delegation for dynamically rendered elements
document.addEventListener("click", (e) => {
  const profileBtn = e.target.closest("#authBtn");
  if (!profileBtn) return;

  toggleProfileMenu();
});

function initializeAppCore() {
  console.log("📦 Loading user data...");
  loadUserData();

  // Initialize chat with welcome message
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) {
    // Welcome message already in HTML
  }

  // Set up smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  // Listen for page visibility changes to reload appointments when user returns
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      console.log(
        "📋 Page visible again - reloading appointments and notifications..."
      );
      loadUserData();
      loadNotificationCountSafe(); // Refresh notification badge
    }
  });

  // Listen for localStorage changes from other tabs/pages
  window.addEventListener("storage", (e) => {
    if (e.key === "medicsense_appointments") {
      console.log("📋 Appointments updated in another tab - reloading...");
      loadUserData();
    }
    if (e.key === "medicsense_unread_count") {
      console.log(
        "🔔 Notification count updated in another tab - refreshing badge..."
      );
      loadNotificationCountSafe();
    }
  });

  console.log("✅ Core app initialized");
}

// ========================================
// AUTHENTICATION INITIALIZATION - WITH TIMEOUT
// ========================================

// Timeout wrapper for Firebase initialization
function initializeAuthWithTimeout(timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    let resolved = false;

    // Timeout safety
    const timeout = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        console.warn(`⚠️ Auth initialization timed out after ${timeoutMs}ms`);
        reject(new Error("Auth initialization timeout"));
      }
    }, timeoutMs);

    // Try to initialize auth
    const tryInit = () => {
      if (resolved) return;

      if (window.firebaseAuth) {
        clearTimeout(timeout);
        resolved = true;
        setupAuthListener();
        resolve();
      } else {
        console.log("⏳ Waiting for Firebase to load...");

        // Set up one-time listener with timeout
        const onReady = () => {
          if (resolved) return;
          clearTimeout(timeout);
          resolved = true;
          console.log("✅ Firebase ready event received");
          setupAuthListener();
          resolve();
        };

        window.addEventListener("firebase-ready", onReady, { once: true });

        // Also check periodically in case event was missed
        let checks = 0;
        const checkInterval = setInterval(() => {
          checks++;
          if (resolved || checks > 10) {
            clearInterval(checkInterval);
            return;
          }

          if (window.firebaseAuth) {
            clearInterval(checkInterval);
            clearTimeout(timeout);
            resolved = true;
            setupAuthListener();
            resolve();
          }
        }, 500);
      }
    };

    tryInit();
  });
}

function setupAuthListener() {
  if (!window.firebaseAuth) {
    console.error("❌ Firebase auth not available");
    return;
  }

  const { auth, onAuthStateChanged } = window.firebaseAuth;

  console.log("🔐 Setting up auth state listener...");

  // THIS IS THE SINGLE SOURCE OF TRUTH FOR AUTH STATE
  onAuthStateChanged(auth, (user) => {
    console.log(
      "🔐 Auth state changed:",
      user ? `Logged in as ${user.email || user.uid}` : "Logged out"
    );

    if (user) {
      // User is authenticated
      console.log("✅ User authenticated:", {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
      });

      // CRITICAL: Get token and save complete state
      user
        .getIdToken()
        .then(async (token) => {
          await saveAuthState(user, token);
          state.currentUser = user.uid;
          updateAuthUI(user);

          // ONLY close modal if it's currently open AND user just logged in
          const modal = document.getElementById("authModal");
          if (modal && modal.style.display === "flex") {
            console.log("📴 Closing auth modal after successful login");
            console.log(
              "🔒 Setting AUTH_MODAL_CLOSED_BY_LOGIN flag to prevent reopening"
            );
            closeAuthModal();

            // Show success message after a short delay to ensure modal is closed
            setTimeout(() => {
              showToast(
                `Welcome back, ${user.displayName || user.email || "User"}!`,
                "success"
              );
            }, 300);
          } else {
            console.log("ℹ️ Modal already closed or wasn't open");
          }

          // Save user ID to localStorage (legacy support)
          localStorage.setItem("medicsense_user_id", user.uid);

          // Load notifications now that user is authenticated
          loadNotificationCountSafe().catch((err) => {
            console.warn("⚠️ Failed to load notifications:", err);
          });
        })
        .catch((error) => {
          console.error("❌ Failed to get ID token:", error);
          // Still update UI even if token fetch fails
          saveAuthState(user, null);
          state.currentUser = user.uid;
          updateAuthUI(user);
        });
    } else {
      // User is logged out
      console.log("ℹ️ User logged out");

      // CRITICAL: Clear auth state completely
      clearAuthState();
      state.currentUser = null;
      updateAuthUI(null);

      // Restore auth modal to login state (but DON'T show it)
      restoreAuthModal();
    }

    // Always reset loading state when auth resolves
    setAuthLoading(false);
  });
}

// Helper functions for safe user data extraction
function getSafeName(user) {
  if (!user) return "Guest";
  if (user.displayName) return user.displayName;
  if (user.email) return user.email.split("@")[0];
  if (user.phoneNumber) return user.phoneNumber;
  return "User";
}

function getSafeEmail(user) {
  if (!user) return "";
  return user.email || user.phoneNumber || "No email";
}

// ─── Google's exact 8 account avatar colors ──────────────────────────────────
// Same 8 colors Google uses for accounts without a real profile photo.
// Color is picked by hashing email/uid — consistent across sessions.
const GOOGLE_AVATAR_COLORS = [
  '4285F4', // Google Blue
  'DB4437', // Google Red
  '0F9D58', // Google Green
  'F4B400', // Google Yellow
  'AB47BC', // Purple
  '00ACC1', // Teal
  'FF7043', // Deep Orange
  'E91E63', // Pink
];

function getAvatarColor(seedStr) {
  let hash = 0;
  const s = (seedStr || 'user').toLowerCase();
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return GOOGLE_AVATAR_COLORS[hash % GOOGLE_AVATAR_COLORS.length];
}

// Returns true if the photoURL is Google's auto-generated avatar (not a real uploaded photo).
// Google auto-generated avatar URLs typically contain "googleusercontent.com" and end with a size param
// OR look like https://lh3.googleusercontent.com/a/... (personalized photo set by user)
// We consider it "real" only if it's NOT the default generated one.
// Simplest reliable check: if the URL contains "=s96-c" it's the default icon size thumbnail.
function isGoogleAutoAvatar(photoURL) {
  if (!photoURL) return true;
  // Google auto-generated avatars always include these size/crop params
  return /=s\d+-c/.test(photoURL) || photoURL.includes('accounts.google.com/v3/signin');
}

// Build an SVG data URI avatar — one letter, Google color, clean flat circle.
function buildAvatarSVG(name, seed) {
  const letter = (name || 'U').charAt(0).toUpperCase();
  const color  = '#' + getAvatarColor(seed || name || 'user');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
    <circle cx="64" cy="64" r="64" fill="${color}"/>
    <text x="64" y="64" dy="0.36em" text-anchor="middle"
      fill="white"
      font-family="Google Sans, Roboto, Arial, sans-serif"
      font-size="60"
      font-weight="500">${letter}</text>
  </svg>`;
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

// Returns the best avatar for a user.
// Uses the actual Google account photo if set, otherwise falls back to our SVG initial.
function getSafePhotoURL(user) {
  if (!user) return null;
  // Use the real Google account photo directly — this is what shows on accounts.google.com
  if (user.photoURL) return user.photoURL;
  // No photo set: generate a clean single-letter SVG with Google colors
  const name = getSafeName(user);
  const seed = user.email || user.uid || name;
  return buildAvatarSVG(name, seed);
}

function getAvatarFallbackURL(name, seed) {
  return buildAvatarSVG(name || 'User', seed || name || 'user');
}


// ========================================
// NAVIGATION FUNCTIONS
// ========================================
function scrollToSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) {
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function toggleMobileMenu() {
  const mobileMenu = document.getElementById("mobileMenu");
  state.isMobileMenuOpen = !state.isMobileMenuOpen;
  if (state.isMobileMenuOpen) {
    mobileMenu.classList.add("active");
  } else {
    mobileMenu.classList.remove("active");
  }
}

function toggleSearch() {
  showToast("Search feature coming soon!", "info");
}

function showNotifications() {
  window.location.href = "notifications.html";
}

// Load notification count with timeout and error handling
function getUserId() {
  if (state.currentUser) return state.currentUser;

  // Try to get from localStorage
  const savedId = localStorage.getItem("medicsense_user_id");
  if (savedId) return savedId;

  // Default to config user ID (guest)
  return CONFIG.USER_ID;
}

// Load notification count with timeout and error handling
async function loadNotificationCountSafe() {
  try {
    const userId = getUserId();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(
      `${
        CONFIG.API_BASE_URL
      }/notifications/summary?user_id=${encodeURIComponent(userId)}`,
      { signal: controller.signal }
    );

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const summary = data && data.summary ? data.summary : null;

    const unreadCount =
      summary && typeof summary.unread === "number" ? summary.unread : 0;

    console.log("🔔 Notification badge update - Unread count:", unreadCount);

    const badge = document.getElementById("notificationBadge");
    if (badge) {
      if (unreadCount > 0) {
        badge.textContent = unreadCount > 99 ? "99+" : unreadCount;
        badge.classList.remove("hidden");
        badge.style.display = "flex";
        console.log("✅ Badge shown with count:", badge.textContent);
      } else {
        badge.textContent = "";
        badge.classList.add("hidden");
        badge.style.display = "none";
        console.log("✅ Badge hidden (0 unread)");
      }
    }
  } catch (error) {
    if (error.name === "AbortError") {
      console.warn("⚠️ Notification loading timed out");
    } else {
      console.warn("⚠️ Could not load notifications:", error.message);
    }

    const badge = document.getElementById("notificationBadge");
    if (badge) {
      badge.style.display = "none";
    }
  }
}

// Alias for user-preferred naming
async function updateBellBadge() {
  await loadNotificationCountSafe();
}

async function fetchNotifications() {
  console.log("🔔 Re-fetching notifications after action...");
  await updateBellBadge();
}

// Legacy function for backward compatibility - now calls safe version
async function loadNotificationCount() {
  return loadNotificationCountSafe();
}

// Refresh notification count periodically (every 30 seconds)
setInterval(() => {
  if (document.visibilityState === "visible") {
    loadNotificationCount();
  }
}, 30000);

function closeAlert() {
  const alertBar = document.getElementById("alertBar");
  if (alertBar) {
    alertBar.style.display = "none";
  }
}

// ========================================
// SYMPTOM CHECKER FUNCTIONS
// ========================================
function updateSeverityDisplay() {
  const slider = document.getElementById("severityRange");
  const valueDisplay = document.getElementById("severityValue");

  if (slider && valueDisplay) {
    const update = () => {
      valueDisplay.textContent = slider.value === "0" ? "-" : slider.value;
    };
    slider.addEventListener("input", update);
    slider.addEventListener("change", update); // Ensure updates on release
    // Initialize
    update();
  }
}

// Input validation for symptom textarea
// Input validation for symptom checker form (Judge-Ready)
function setupSymptomInputValidation() {
  const symptomInput = document.getElementById("symptomInput");
  const durationSelect = document.getElementById("symptomDuration");
  const severitySlider = document.getElementById("severityRange");
  const severityValue = document.getElementById("severityValue");
  const analyzeBtn = document.getElementById("analyzeBtn");

  if (!symptomInput || !analyzeBtn) return;

  const checkValidity = () => {
    const hasSymptoms = symptomInput.value.trim().length >= 3;
    const hasDuration = durationSelect.value !== "";
    const hasSeverity = parseInt(severitySlider.value) > 0;

    analyzeBtn.disabled = !(hasSymptoms && hasDuration && hasSeverity);
  };

  // Severity Slider Feedback
  if (severitySlider && severityValue) {
    severitySlider.addEventListener("input", (e) => {
      severityValue.textContent = e.target.value;
      checkValidity();
    });
  }

  // Symptom Input Validation
  symptomInput.addEventListener("input", checkValidity);

  // Duration Selection Validation
  if (durationSelect) {
    durationSelect.addEventListener("change", checkValidity);
  }

  // Final Hardening: JS-only binding (STEP 2)
  analyzeBtn.addEventListener("click", analyzeSymptoms);

  // Initialize state
  checkValidity();
}

function addSymptom(symptom, element) {
  const textarea = document.getElementById("symptomInput");

  // Toggle visual state if element is provided
  if (element) {
    element.classList.toggle("active");
  }

  if (textarea) {
    const currentText = textarea.value.trim();
    const symptomTag = symptom.trim();

    // Check if symptom is already in list (simple check)
    if (currentText.toLowerCase().includes(symptomTag.toLowerCase())) {
      // Remove it (Toggle OFF) behavior
      // Note: This is a simple string replacement. Ideally, we'd parse comma-separated values.
      // For now, we'll just remove the specific instance to support the "Toggle" feel.
      // Logic: Split by comma, filter out the symptom, join back.
      const parts = currentText
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.toLowerCase() !== symptomTag.toLowerCase());
      textarea.value = parts.join(", ");

      // If we just removed it, ensure the tag is visually inactive
      if (element) element.classList.remove("active");
    } else {
      // Add it (Toggle ON)
      if (currentText) {
        textarea.value = currentText + ", " + symptomTag;
      } else {
        textarea.value = symptomTag;
      }
      // Ensure tag is visually active
      if (element) element.classList.add("active");
    }

    textarea.focus();

    // Trigger validation re-check
    const analyzeBtn = document.getElementById("analyzeBtn");
    if (analyzeBtn) {
      const durationSelect = document.getElementById("symptomDuration");
      const severitySlider = document.getElementById("severityRange");

      const hasSymptoms = textarea.value.trim().length >= 3;
      const hasDuration = durationSelect ? durationSelect.value !== "" : false;
      const hasSeverity = severitySlider
        ? parseInt(severitySlider.value) > 0
        : false;

      analyzeBtn.disabled = !(hasSymptoms && hasDuration && hasSeverity);
    }
  }
}

async function analyzeSymptoms() {
  // ✅ Rule 1: Immediate lock at the absolute top
  if (isAnalyzing) return;
  isAnalyzing = true;

  // Step 2: HARD GUARD + LOADER (AT TOP)
  const symptomInput = document.getElementById("symptomInput");
  const durationSelect = document.getElementById("symptomDuration");
  const severitySlider = document.getElementById("severityRange");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const resultsBody = document.getElementById("symptomResultsBody");
  const infoCard = document.getElementById("symptomInfoCard");
  const resultsCard = document.getElementById("symptomResults");
  const layoutContainer = document.querySelector(".symptom-checker-container");

  if (
    !symptomInput ||
    !durationSelect ||
    !severitySlider ||
    !analyzeBtn ||
    !resultsBody
  ) {
    isAnalyzing = false;
    return;
  }

  const symptomText = symptomInput.value.trim();
  const durationVal = durationSelect.value;
  const severityVal = Number(severitySlider.value);

  // 🛡️ Rule 2: Mandatory Validation Guard
  if (!symptomText || !durationVal || severityVal <= 0) {
    showToast("Please complete all required fields.", "warning");
    isAnalyzing = false;
    return;
  }

  // 🚀 Rule 3: Loading state must appear IMMEDIATELY after validation
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

  if (resultsCard) resultsCard.style.display = "block";
  if (infoCard) infoCard.style.display = "none";
  if (layoutContainer) layoutContainer.classList.add("has-analysis");

  resultsBody.innerHTML = `
    <div class="loading-state">
      <div class="loading-spinner"></div>
      <h3>Analyzing your symptoms...</h3>
      <p>This may take a few moments</p>
    </div>
  `;

  // 🧱 Rule 4: ONE async lifecycle (FETCH + RENDER ONLY HERE)
  try {
    const response = await fetchWithTimeout(
      `${CONFIG.API_BASE_URL}/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Analyze these symptoms: ${symptomText}. Duration: ${durationVal}. Severity: ${severityVal}/10.`,
          user_id: state.currentUser || `guest_${sessionStorage.getItem('medicsense_session') || Date.now()}`,
        }),
      },
      15000
    );

    const payload = await response.json();

    if (payload.data && payload.data.reply) {
      displaySymptomResults(payload.data.reply, severityVal);
      // Backend track
      state.symptoms.push({
        symptoms: symptomText,
        duration: durationVal,
        severity: severityVal,
        analysis: payload.data.reply,
        timestamp: new Date().toISOString(),
      });
      saveUserData();
    } else {
      throw new Error("No response from AI");
    }
  } catch (error) {
    console.error("Error analyzing symptoms:", error);
    resultsBody.innerHTML = `
      <div class="error-message">
        <i class="fas fa-exclamation-circle"></i>
        <p>Unable to analyze symptoms. Please try again.</p>
      </div>
    `;
    showToast("Unable to analyze symptoms. Please try again.", "error");
  } finally {
    // 🔒 Rule 5: Lock release ONLY in finally
    isAnalyzing = false;
    if (analyzeBtn) {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = '<i class="fas fa-brain"></i> Analyze with AI';
    }
  }
}

function displaySymptomResults(analysis, severity) {
  const resultsBody = document.getElementById("symptomResultsBody");
  if (!resultsBody) return;

  const severityColor = severity <= 6 ? "warning" : "danger";
  const severityText =
    severity <= 3 ? "Mild" : severity <= 6 ? "Moderate" : "Severe";

  // Pre-process AI response for better formatting
  let formattedAnalysis = analysis
    .replace(/•/g, "\n- ") // Convert bullets to markdown list items
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Convert ALL **text** to bold
    .replace(/\*\*/g, "") // Remove any potential stray asterisks
    .replace(
      /(My Recommendations:|Self-Care Tips:)/g,
      "\n\n<strong>$1</strong>\n"
    ); // Ensure headers have spacing

  // Parse AI response
  const analysisHTML =
    typeof marked !== "undefined"
      ? marked.parse(formattedAnalysis)
      : formattedAnalysis.replace(/\n/g, "<br>");

  resultsBody.innerHTML = `
    <!-- Severity Badge -->
    <div class="severity-badge ${severityColor}">
      <i class="fas fa-info-circle"></i>
      Severity: ${severityText} (${severity}/10)
    </div>

    <!-- Summary Section -->
    <div class="results-section results-summary">
      <div class="analysis-text">${analysisHTML}</div>
    </div>
  `;

  showToast("Symptom analysis complete!", "success");
}

function bookAppointmentFromSymptom() {
  scrollToSection("appointments");
  showToast("Please fill in appointment details", "info");
}

// ── Improvement 5: Lazy-load html2canvas on first use ──────────────────
function lazyLoadHtml2Canvas() {
  return new Promise((resolve, reject) => {
    if (typeof html2canvas !== "undefined") { resolve(); return; }
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js";
    script.onload = resolve;
    script.onerror = () => reject(new Error("Failed to load html2canvas"));
    document.head.appendChild(script);
  });
}

function exportSymptomReport() {
  const element = document.getElementById("symptomResults");
  if (!element || element.style.display === "none") {
    showToast("No report to download", "warning");
    return;
  }

  showToast("Generating image report...", "info");

  lazyLoadHtml2Canvas().then(() => {
  // Inject Timestamp temporarily
  const timestampDiv = document.createElement("div");
  timestampDiv.innerHTML = `<p style="color: #6b7280; font-size: 0.875rem; margin-bottom: 1rem;"><strong>Report Generated:</strong> ${new Date().toLocaleString()}</p>`;
  element.prepend(timestampDiv);

  html2canvas(element, {
    useCORS: true,
    scale: 2,
    backgroundColor: "#ffffff",
    ignoreElements: (el) => el.classList.contains("results-actions"),
  })
    .then((canvas) => {
      try {
        const link = document.createElement("a");
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `MedicSense_Report_${timestamp}.png`;
        link.href = canvas.toDataURL("image/png");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("Report downloaded as image!", "success");
      } catch (err) {
        console.error("Download failed:", err);
        showToast("Failed to save image.", "error");
      } finally {
        timestampDiv.remove();
      }
    })
    .catch((err) => {
      console.error("Image generation failed:", err);
      timestampDiv.remove();
      showToast("Failed to generate image report.", "error");
    });
  }).catch(() => showToast("Could not load screenshot library.", "error"));
}

// ========================================
// VOICE INPUT - PRODUCTION-READY IMPLEMENTATION
// ========================================
// CRITICAL: recognition.start() MUST be called synchronously in user gesture context
// Event delegation ensures the click handler runs immediately without async delays

document.addEventListener("click", (e) => {
  // Check if clicked element is a voice input button
  const btn = e.target.closest("#voiceInputBtnSymptom, #voiceInputBtnChat");
  if (!btn) return;

  const voiceType = btn.dataset.voiceType; // "symptom" or "chat"
  startVoiceInput(voiceType);
});

// Global variable to track active voice recognition
let currentRecognition = null;

function startVoiceInput(type) {
  // Check browser support
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    showToast("Voice input not supported in this browser", "error");
    return;
  }

  // Get the button that was clicked
  const buttonId =
    type === "symptom" ? "voiceInputBtnSymptom" : "voiceInputBtnChat";
  const button = document.getElementById(buttonId);

  if (!button) {
    console.error("Voice input button not found:", buttonId);
    return;
  }

  // IF ALREADY LISTENING, STOP IT
  if (currentRecognition) {
    console.log("🛑 Stopping active voice input...");
    currentRecognition.stop();
    currentRecognition = null;
    return; // onend will handle UI reset
  }

  // Helper function to set button to listening state
  function setListeningState() {
    button.classList.add("voice-listening");
    button.disabled = false; // Allow user to click to stop!

    // Update button text if it has text content
    const buttonText =
      button.querySelector("span") ||
      button.childNodes[button.childNodes.length - 1];
    if (buttonText && buttonText.nodeType === Node.TEXT_NODE) {
      buttonText.textContent = " Stop Listening";
    } else if (button.innerText && button.innerText.includes("Voice Input")) {
      // For buttons with text
      const icon = button.querySelector("i");
      button.innerHTML = "";
      if (icon) {
        // Change icon to stop circle if possible, or keep formatting
        icon.className = "fas fa-stop-circle";
        button.appendChild(icon);
      }
      button.appendChild(document.createTextNode(" Stop Listening"));
    }
  }

  // Helper function to reset button to default state
  function resetButtonState() {
    button.classList.remove("voice-listening");
    button.disabled = false;
    currentRecognition = null; // Clear global state

    // Restore original button text if it has text content
    const buttonText =
      button.querySelector("span") ||
      button.childNodes[button.childNodes.length - 1];
    if (buttonText && buttonText.nodeType === Node.TEXT_NODE) {
      buttonText.textContent = " Voice Input";
    } else {
      // Restore original text for buttons with text
      button.innerHTML = '<i class="fas fa-microphone"></i> Voice Input';
    }
  }

  // Create new recognition instance per click (do NOT reuse)
  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = function () {
    console.log("🎤 Voice listening started");
    currentRecognition = recognition; // Set global
    setListeningState();
    showToast("🎤 Listening... Tap to stop", "info");
  };

  recognition.onresult = function (event) {
    const transcript = event.results[0][0].transcript;
    console.log("🎧 Voice result:", transcript);

    // Insert transcript into appropriate input field
    if (type === "symptom") {
      const symptomInput = document.getElementById("symptomInput");
      if (symptomInput) {
        symptomInput.value = transcript;
      }
    } else if (type === "chat") {
      const chatInput = document.getElementById("chatInput");
      if (chatInput) {
        chatInput.value = transcript;
      }
    }

    showToast("✅ Voice input captured!", "success");
  };

  recognition.onerror = function (event) {
    console.error("❌ Voice error:", event.error);

    // Ignore "aborted" error if user manually stopped it
    if (event.error === "aborted") {
      resetButtonState();
      return;
    }

    // Reset button state on error
    resetButtonState();

    // Provide user-friendly error messages
    let errorMessage = "Voice input error";
    switch (event.error) {
      case "not-allowed":
      case "permission-denied":
        errorMessage =
          "🚫 Microphone access denied. Please allow microphone access in your browser settings.";
        break;
      case "no-speech":
        errorMessage =
          "🔇 No speech detected. Please try again and speak clearly.";
        break;
      case "audio-capture":
        errorMessage =
          "🎤 No microphone found. Please connect a microphone and try again.";
        break;
      case "network":
        errorMessage =
          "🌐 Network error. Please check your internet connection.";
        break;
      default:
        errorMessage = `Voice input error: ${event.error}`;
    }

    showToast(errorMessage, "error");
  };

  recognition.onend = function () {
    console.log("🛑 Voice input ended");
    resetButtonState();
  };

  // CRITICAL: Call start() immediately
  try {
    recognition.start();
  } catch (error) {
    console.error("Failed to start voice input:", error);
    resetButtonState();
    showToast("Failed to start voice input. Please try again.", "error");
  }
}

// Legacy function stubs for backward compatibility (if called elsewhere)
function useVoiceInput(type) {
  startVoiceInput(type);
}

function toggleVoiceInput() {
  startVoiceInput("chat");
}

// ========================================
// APPOINTMENT FUNCTIONS
// ========================================
async function loadAvailableSlots() {
  const doctorSelect = document.getElementById("doctorSelect");
  const dateInput = document.getElementById("appointmentDate");
  const timeSelect = document.getElementById("appointmentTime");
  const slotsGrid = document.getElementById("slotsGrid");

  if (!doctorSelect || !dateInput || !doctorSelect.value || !dateInput.value) {
    if (slotsGrid) {
      slotsGrid.innerHTML =
        '<p class="slots-hint">Please select doctor and date</p>';
    }
    return;
  }

  try {
    // Call API to get available slots
    const response = await fetchWithTimeout(
      `${CONFIG.API_BASE_URL}/appointments/slots?doctor=${encodeURIComponent(
        doctorSelect.value
      )}&date=${encodeURIComponent(dateInput.value)}`,
      {},
      5000 // 5 second timeout
    );
    const data = await response.json();

    let slots = [];
    if (data.success && data.slots && data.slots.length > 0) {
      slots = data.slots;
    } else {
      // Fallback to mock slots if API fails
      slots = [
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
        "14:00",
        "14:30",
        "15:00",
        "15:30",
        "16:00",
        "16:30",
      ];
    }

    // Update time select
    if (timeSelect) {
      timeSelect.innerHTML = '<option value="">Select time slot</option>';
      slots.forEach((slot) => {
        const option = document.createElement("option");
        option.value = slot;
        option.textContent = slot;
        timeSelect.appendChild(option);
      });
    }

    // Update slots grid
    if (slotsGrid) {
      slotsGrid.innerHTML = slots
        .map(
          (slot) => `
            <button class="slot-btn available" onclick="selectSlot('${slot}')">
                ${slot}
            </button>
        `
        )
        .join("");
    }
  } catch (error) {
    console.error("Error loading slots:", error);
    // Fallback to mock slots on error
    const slots = [
      "09:00",
      "09:30",
      "10:00",
      "10:30",
      "11:00",
      "11:30",
      "14:00",
      "14:30",
      "15:00",
      "15:30",
      "16:00",
      "16:30",
    ];

    if (timeSelect) {
      timeSelect.innerHTML = '<option value="">Select time slot</option>';
      slots.forEach((slot) => {
        const option = document.createElement("option");
        option.value = slot;
        option.textContent = slot;
        timeSelect.appendChild(option);
      });
    }

    if (slotsGrid) {
      slotsGrid.innerHTML = slots
        .map(
          (slot) => `
            <button class="slot-btn available" onclick="selectSlot('${slot}')">
                ${slot}
            </button>
        `
        )
        .join("");
    }
  }
}

function selectSlot(time) {
  const timeSelect = document.getElementById("appointmentTime");
  if (timeSelect) {
    timeSelect.value = time; // Existing logic - updates hidden select
    timeSelect.dispatchEvent(new Event("change")); // Fix: Trigger change event to clear errors
    showToast(`Selected ${time}`, "success"); // Existing logic

    // NEW: Visual feedback for premium time-slot grid
    document.querySelectorAll(".slot-btn").forEach((btn) => {
      btn.classList.remove("selected");
    });

    // Add selected class to clicked button
    const clickedBtn = event?.target;
    if (clickedBtn && clickedBtn.classList.contains("slot-btn")) {
      clickedBtn.classList.add("selected");
    }

    // Update the selected time display indicator
    const selectedTimeDisplay = document.getElementById("selectedTimeDisplay");
    if (selectedTimeDisplay) {
      selectedTimeDisplay.textContent = `✓ Selected: ${time}`;
      selectedTimeDisplay.style.background =
        "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)";
      selectedTimeDisplay.style.borderColor = "#60a5fa";
      selectedTimeDisplay.style.color = "#1e40af";
      selectedTimeDisplay.style.fontWeight = "600";
    }
  }
}

async function bookAppointment() {
  console.log("🚀 Booking appointment initiated - Validation Active");

  // Clear previous errors first
  document.querySelectorAll(".is-invalid").forEach((el) => {
    el.classList.remove("is-invalid");
  });
  document.querySelectorAll(".invalid-feedback").forEach((el) => el.remove());

  const nameInput = document.getElementById("patientName");
  const phoneInput = document.getElementById("patientPhone");
  const emailInput = document.getElementById("patientEmail");
  const doctorSelect = document.getElementById("doctorSelect");
  const dateInput = document.getElementById("appointmentDate");
  const timeInput = document.getElementById("appointmentTime");
  const reasonInput = document.getElementById("appointmentReason");

  // Helper to get value safely
  const getValue = (el) => (el ? el.value.trim() : "");

  const name = getValue(nameInput);
  const phone = getValue(phoneInput);
  const email = getValue(emailInput);
  const doctor = getValue(doctorSelect);
  const date = getValue(dateInput);
  const time = getValue(timeInput);
  const reason = getValue(reasonInput);

  const typeInput = document.querySelector(
    'input[name="appointmentType"]:checked'
  );
  const type = typeInput ? typeInput.value : "";

  let isValid = true;
  let firstErrorField = null;

  // Validation Helper
  const setError = (input, msg) => {
    if (!input) return;
    isValid = false;
    input.classList.add("is-invalid");

    // Create or update feedback
    let feedback = input.parentNode.querySelector(".invalid-feedback");
    if (!feedback) {
      feedback = document.createElement("div");
      feedback.className = "invalid-feedback";
      input.parentNode.appendChild(feedback);
    }
    feedback.textContent = msg;
    feedback.style.display = "block"; // Ensure visibility

    // Track first error for scrolling
    if (!firstErrorField) firstErrorField = input;

    // Auto-clear on input
    const clearError = () => {
      input.classList.remove("is-invalid");
      const fb = input.parentNode.querySelector(".invalid-feedback");
      if (fb) fb.remove();
      input.removeEventListener("input", clearError);
      input.removeEventListener("change", clearError);
    };

    input.addEventListener("input", clearError);
    input.addEventListener("change", clearError);
  };

  // 1. Validate Name
  if (!name) {
    setError(nameInput, "Full Name is required");
  } else if (name.length < 2) {
    setError(nameInput, "Name must be at least 2 characters");
  }

  // 2. Validate Phone
  // Allow format like: +91 9876543210, 9876543210, 09876543210, 987-654-3210
  const phoneRegex = /^(\+?\d{1,4}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?[\d\s-]{5,15}$/;
  if (!phone) {
    setError(phoneInput, "Phone Number is required");
  } else if (!phoneRegex.test(phone.replace(/\s+/g, ""))) {
    setError(phoneInput, "Enter a valid phone number (10-15 digits)");
  }

  // 3. Validate Email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email) {
    setError(emailInput, "Email is required");
  } else if (!emailRegex.test(email)) {
    setError(emailInput, "Enter a valid email address");
  }

  // 4. Validate Doctor
  if (!doctor) {
    setError(doctorSelect, "Please select a doctor or department");
  }

  // 5. Validate Date
  if (!date) {
    setError(dateInput, "Preferred Date is required");
  } else {
    // Optional: Check for past dates
    const selectedDate = new Date(date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (selectedDate < today) {
      setError(dateInput, "Date cannot be in the past");
    }
  }

  // 6. Validate Time
  if (!time) {
    setError(timeInput, "Preferred Time is required");

    // Visual cue for custom slot grid (if hidden select is used)
    const slotsGrid = document.getElementById("slotsGrid");
    if (slotsGrid && timeInput.style.display === "none") {
      slotsGrid.style.border = "1px solid #ef4444";
      slotsGrid.style.borderRadius = "8px";
      slotsGrid.style.padding = "8px";

      // Error message removed as per user request

      // Auto-clear logic for grid
      const clearGridError = () => {
        slotsGrid.style.border = "";
        slotsGrid.style.padding = "";
        const ge = slotsGrid.parentNode.querySelector(".grid-error-msg");
        if (ge) ge.remove();
      };
      // Hook into the selectSlot function indirectly or add listener to hidden input
      timeInput.addEventListener("change", clearGridError);
      // Also modify selectSlot to trigger this if needed, but 'change' event on hidden input might not fire automatically
      // So we add a click listener to grid to reset visual state tentatively
      slotsGrid.addEventListener(
        "click",
        () => {
          setTimeout(() => {
            if (timeInput.value) clearGridError();
          }, 100);
        },
        { once: true }
      );
    }
  }

  // 7. Validate Type
  if (!type) {
    const typeContainer = document.querySelector(".appointment-type");
    if (typeContainer) {
      let feedback = typeContainer.querySelector(".invalid-feedback");
      if (!feedback) {
        feedback = document.createElement("div");
        feedback.className = "invalid-feedback";
        feedback.style.display = "block";
        feedback.textContent = "Please select an appointment type";
        typeContainer.appendChild(feedback);
      }
      if (!firstErrorField) firstErrorField = typeContainer;

      // Clear on change
      const types = document.getElementsByName("appointmentType");
      types.forEach((t) =>
        t.addEventListener(
          "change",
          () => {
            const existingFeedback =
              typeContainer.querySelector(".invalid-feedback");
            if (existingFeedback) existingFeedback.remove();
          },
          { once: true }
        )
      );
    }
    isValid = false;
  }

  if (!isValid) {
    if (firstErrorField) {
      // Smooth scroll to first error
      firstErrorField.scrollIntoView({ behavior: "smooth", block: "center" });
      // Focus if it's an input
      if (firstErrorField.focus) {
        firstErrorField.focus({ preventScroll: true });
      }

      // Shake animation effect for better feedback (optional, using CSS class)
      firstErrorField.classList.add("animate__animated", "animate__headShake");
      setTimeout(() => {
        firstErrorField.classList.remove(
          "animate__animated",
          "animate__headShake"
        );
      }, 500);
    }
    showToast("Please correct the errors in the form.", "error");
    return;
  }

  // Show loading
  showToast("Booking your appointment...", "info");

  // NEW: Add loading state to button
  const bookBtn = document.querySelector(".btn-book-appointment");
  if (bookBtn) {
    bookBtn.classList.add("btn-loading");
    bookBtn.disabled = true;
    // Add spinner to button text
    const originalBtnText = bookBtn.innerHTML;
    bookBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Booking...';

    // Restore function
    var restoreBtn = () => {
      bookBtn.classList.remove("btn-loading");
      bookBtn.disabled = false;
      bookBtn.innerHTML = originalBtnText;
    };
  }

  try {
    // Get user ID - use Firebase UID if logged in, or consistent guest ID
    let userId = getUserId();

    // If getUserId returned null or undefined (shouldn't happen with current logic but for safety)
    if (!userId) {
      userId = "guest_" + Math.random().toString(36).substr(2, 9);
      console.warn("⚠️ Generated new guest ID.");
    }

    // Persist user ID to localStorage so notifications.html can see it
    if (!state.currentUser) {
      localStorage.setItem("medicsense_user_id", userId);
    }

    // Call backend API to book appointment
    const response = await fetchWithTimeout(
      `${CONFIG.API_BASE_URL}/appointments/book`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: userId,
          name,
          phone,
          email,
          doctorId: doctor,
          date,
          time,
          reason,
          type,
        }),
      },
      10000
    ); // 10 second timeout

    const data = await response.json();

    if (data.success) {
      playSuccessSound(); // Play confirmation sound
      const appointment = {
        id: data.appointmentId || "apt_" + Date.now(),
        name,
        phone,
        email,
        doctor,
        doctorId: doctor,
        date,
        time,
        reason,
        type,
        status: "confirmed",
        timestamp: new Date().toISOString(),
      };

      state.appointments.push(appointment);
      saveUserData();

      // Show success
      showToast(
        "Appointment booked successfully! Confirmation sent to your email.",
        "success"
      );

      // NEW: Show success animation
      if (typeof showSuccessAnimation === "function") {
        showSuccessAnimation();
      }

      // 🔥 REQUIRED: Re-fetch notifications so the bell dot appears immediately
      fetchNotifications();

      // Reset form
      document.getElementById("patientName").value = "";
      document.getElementById("patientPhone").value = "";
      document.getElementById("patientEmail").value = "";
      document.getElementById("doctorSelect").value = "";
      document.getElementById("appointmentDate").value = "";
      document.getElementById("appointmentTime").value = "";
      document.getElementById("appointmentReason").value = "";

      // Remove all validation classes (success/error states)
      document.querySelectorAll(".is-valid").forEach((el) => {
        el.classList.remove("is-valid");
      });
      document.querySelectorAll(".is-invalid").forEach((el) => {
        el.classList.remove("is-invalid");
      });
      document.querySelectorAll(".field-valid").forEach((el) => {
        el.classList.remove("field-valid");
      });
      document.querySelectorAll(".field-invalid").forEach((el) => {
        el.classList.remove("field-invalid");
      });
      document
        .querySelectorAll(".invalid-feedback")
        .forEach((el) => el.remove());
      document.querySelectorAll(".valid-feedback").forEach((el) => el.remove());

      // Reset all form-control styling
      document.querySelectorAll(".form-control").forEach((el) => {
        el.style.borderColor = "";
        el.style.background = "";
      });

      // Reset selected time display
      const selectedTimeDisplay = document.getElementById(
        "selectedTimeDisplay"
      );
      if (selectedTimeDisplay) {
        selectedTimeDisplay.textContent = "Select from available slots →";
        selectedTimeDisplay.style.background = "#f8fafc";
        selectedTimeDisplay.style.borderColor = "#cbd5e1";
        selectedTimeDisplay.style.color = "#64748b";
        selectedTimeDisplay.style.fontWeight = "400";
      }

      // Reset slots grid selection
      document
        .querySelectorAll(".slot-btn")
        .forEach((btn) => btn.classList.remove("selected"));

      // Clear the slots grid
      const slotsGrid = document.getElementById("slotsGrid");
      if (slotsGrid) {
        slotsGrid.innerHTML = "";
        slotsGrid.style.border = "";
        slotsGrid.style.padding = "";
      }

      // Reset hints
      const slotsHint = document.getElementById("slotsHint");
      if (slotsHint) {
        slotsHint.textContent =
          "Select doctor and date to view available slots";
        slotsHint.style.display = "block";
      }

      // Reset radio buttons to default (in-person)
      const inPersonRadio = document.querySelector(
        'input[name="appointmentType"][value="in-person"]'
      );
      if (inPersonRadio) {
        inPersonRadio.checked = true;
      }

      // Update appointments list
      updateAppointmentsList();

      // Show appointment confirmation modal (optional)
      showAppointmentConfirmation(appointment);
    } else {
      throw new Error(data.message || "Failed to book appointment");
    }
  } catch (error) {
    console.error("Error booking appointment:", error);
    showToast(
      error.message || "Error booking appointment. Please try again.",
      "error"
    );
  } finally {
    // NEW: Remove loading state from button
    if (bookBtn && restoreBtn) {
      restoreBtn();
    }
  }
}

function updateAppointmentsList() {
  const listElement = document.getElementById("myAppointmentsList");
  if (!listElement) return;

  // Dashboard widget: show only confirmed/upcoming (not cancelled, not past)
  const today = new Date().toISOString().split("T")[0];
  const recentAppointments = state.appointments
    .filter((apt) => apt.status !== "cancelled" && apt.date >= today)
    .sort(
      (a, b) =>
        new Date(b.timestamp || b.date) - new Date(a.timestamp || a.date)
    )
    .slice(0, 3);

  // ── Improvement 4: Rich empty state ───────────────────────────────
  if (recentAppointments.length === 0) {
    listElement.innerHTML = `
      <div style="text-align:center;padding:24px 16px;color:#9ca3af;">
        <div style="font-size:2.5rem;margin-bottom:8px;">📅</div>
        <p style="font-weight:600;color:#6b7280;margin:0 0 4px;">No upcoming appointments</p>
        <p style="font-size:0.82rem;margin:0;">Book one below and it'll appear here</p>
      </div>`;
    return;
  }

  listElement.innerHTML = recentAppointments
    .map(
      (apt) => `
        <div class="appointment-card" data-id="${apt.id}" id="apt_${apt.id}">
            <div class="appointment-info">
                <h4>${apt.doctor || "Doctor"}</h4>
                <p><i class="fas fa-calendar-alt"></i> ${apt.date} at ${
        apt.time
      }</p>
                <span class="status-badge ${apt.status}">${
        apt.status.charAt(0).toUpperCase() + apt.status.slice(1)
      }</span>
            </div>
            <div class="appointment-actions">
              <button class="cancel-btn" data-apt-id="${apt.id}">Cancel</button>
            </div>
        </div>
    `
    )
    .join("");

  // Attach cancel button event listeners (no inline onclick)
  listElement.querySelectorAll(".cancel-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      cancelAppointmentUI(btn.dataset.aptId, btn);
    });
  });
}

async function cancelAppointmentUI(appointmentId, btnElement) {
  const confirmed = confirm(
    "Are you sure you want to cancel this appointment?"
  );
  if (!confirmed) return;

  // Loading state on button
  if (btnElement) {
    btnElement.innerText = "Cancelling...";
    btnElement.disabled = true;
    btnElement.classList.add("cancel-btn--loading");
  }

  const userId = getUserId();
  try {
    const response = await fetchWithTimeout(
      `${CONFIG.API_BASE_URL}/appointments/${appointmentId}/cancel?user_id=${userId}`,
      {
        method: "POST",
      }
    );

    const data = await response.json();
    if (data.success) {
      showToast("Appointment cancelled successfully", "success");

      // Update local state
      const apt = state.appointments.find((a) => a.id === appointmentId);
      if (apt) apt.status = "cancelled";
      saveUserData();

      // Animated card removal
      const card = document.querySelector(
        `.appointment-card[data-id="${appointmentId}"]`
      );
      if (card) {
        card.style.transition = "opacity 0.3s ease, transform 0.3s ease";
        card.style.opacity = "0";
        card.style.transform = "translateY(-10px)";
        setTimeout(() => {
          updateAppointmentsList();
        }, 300);
      } else {
        updateAppointmentsList();
      }

      // Force notification fetch to show the "Cancelled" notification
      fetchNotifications();
    } else {
      showToast(data.message || "Failed to cancel appointment", "error");
      // Restore button
      if (btnElement) {
        btnElement.innerText = "Cancel";
        btnElement.disabled = false;
        btnElement.classList.remove("cancel-btn--loading");
      }
    }
  } catch (error) {
    console.error("Error cancelling appointment:", error);
    showToast("Error connecting to server", "error");
    // Restore button
    if (btnElement) {
      btnElement.innerText = "Cancel";
      btnElement.disabled = false;
      btnElement.classList.remove("cancel-btn--loading");
    }
  }
}

function showAppointmentConfirmation(appointment) {
  const doctorName =
    document.querySelector(
      `#doctorSelect option[value="${appointment.doctor}"]`
    )?.textContent || appointment.doctor;

  showToast(
    `✅ Appointment Confirmed!\nDoctor: ${doctorName}\nDate: ${appointment.date} at ${appointment.time}`,
    "success"
  );
}

// ========================================
// AUDIO FEEDBACK
// ========================================

// Louder, professional "Chime" (Major 3rd: C5 & E5)
function playSuccessSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;

    const ctx = new AudioContext();

    // Create two oscillators for a harmony (C5 and E5)
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    osc1.type = "sine";
    osc2.type = "sine";

    // C5 (523.25 Hz) & E5 (659.25 Hz)
    osc1.frequency.setValueAtTime(523.25, ctx.currentTime);
    osc2.frequency.setValueAtTime(659.25, ctx.currentTime);

    // Connect both to gain
    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    // Volume Envelope: Distinct "Ding"
    // Louder attack (0.5) -> smooth decay
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.5, now + 0.05); // Attack
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8); // Long Decay

    // Start/Stop
    osc1.start(now);
    osc2.start(now);
    osc1.stop(now + 0.8);
    osc2.stop(now + 0.8);
  } catch (e) {
    console.warn("Audio playback failed", e);
  }
}

// ========================================
// CHAT FUNCTIONS
// ========================================
function handleChatKeyPress(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
}

async function sendChatMessage(quickMessage = null) {
  const input = document.getElementById("chatInput");
  const message = quickMessage || input?.value.trim();

  if (!message) return;

  // ── Improvement 3: Input max-length guard ──────────────────────────
  if (message.length > 1000) {
    showToast("Message too long (max 1000 characters)", "warning");
    return;
  }

  // Clear input
  if (input && !quickMessage) input.value = "";

  // Add user message to UI
  addMessageToChat("user", message);

  // Show typing indicator
  showTypingIndicator();

  try {
    // Get or create session ID for AI agent scaling
    let sessionId = localStorage.getItem("chat_session_id");
    if (!sessionId) {
      sessionId = `chat_${Date.now()}_${Math.random()
        .toString(36)
        .substr(2, 9)}`;
      localStorage.setItem("chat_session_id", sessionId);
    }

    const response = await fetchWithTimeout(
      `${CONFIG.API_BASE_URL}/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          user_id: state.currentUser || `guest_${sessionId}`,
          session_id: sessionId,
        }),
      },
      15000
    ); // 15 second timeout for AI chat

    const data = await response.json();

    // Hide typing indicator
    hideTypingIndicator();

    // ── Support both new envelope {success, data:{reply,...}} and old {response,...}
    const aiText = (data.data && data.data.reply) ? data.data.reply : data.response;
    const riskLevel = (data.data && data.data.risk_level) ? data.data.risk_level : null;
    const suggestedAction = (data.data && data.data.suggested_action) ? data.data.suggested_action : null;
    const isEmergency = data.data && data.data.is_emergency;

    if (aiText) {
      // Map new risk_level → severity badge; old severity field as fallback
      const severityValue = riskLevel || (data.severity === 4 ? "critical" : data.severity === 3 ? "high" : data.severity === 2 ? "moderate" : "low");
      // Map new suggested_action → context badge; old type field as fallback
      const contextValue = suggestedAction || data.type || "general";

      addMessageToChat("ai", aiText, {
        context: contextValue,
        severity: severityValue,
        sentiment: data.sentiment,
      });

      // If emergency, show persistent toast
      if (isEmergency) {
        showToast("🚨 EMERGENCY DETECTED — Call 112 / 911 immediately!", "error");
      }

      // Update chat history
      state.chatHistory.push({
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
      });
      state.chatHistory.push({
        role: "ai",
        content: aiText,
        timestamp: new Date().toISOString(),
      });

      saveUserData();
    } else {
      throw new Error(data.error || "No response from AI");
    }

  } catch (error) {
    console.error("Error sending message:", error);
    hideTypingIndicator();

    // ── Improvement 2: Friendly offline / backend-down message ─────────
    const isOffline = !navigator.onLine || error.message?.includes("timed out") || error.message?.includes("Failed to fetch");
    const offlineMsg = isOffline
      ? "🔌 Can't reach the server right now. Please check your connection and try again."
      : "❌ Something went wrong. Please try again in a moment.";

    addMessageToChat("ai", offlineMsg, { context: "error" });
    showToast(isOffline ? "Backend offline — check your connection" : "Error sending message.", "error");
  }
}

function addMessageToChat(role, content, metadata = {}) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}-message`;

  const avatarDiv = document.createElement("div");
  avatarDiv.className = "message-avatar";
  avatarDiv.innerHTML =
    role === "ai"
      ? '<i class="fas fa-robot"></i>'
      : (() => {
          // Use the signed-in user's Google profile photo if available
          const photo = typeof getSafePhotoURL === "function" && AUTHENTICATED_USER
            ? getSafePhotoURL(AUTHENTICATED_USER)
            : null;
          if (photo) {
            return `<img src="${photo}" alt="You"
              style="width:100%;height:100%;border-radius:10px;object-fit:cover;display:block;"
              onerror="this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i>'"
            >`;
          }
          return '<i class="fas fa-user"></i>';
        })();

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = "message-bubble";

  // Handle image display for user messages
  if (role === "user" && metadata.image) {
    bubbleDiv.innerHTML = `
      <p>${content}</p>
      <img src="${metadata.image}" alt="Uploaded image" style="max-width: 100%; border-radius: 8px; margin-top: 8px; max-height: 300px; object-fit: contain;">
    `;
  } else if (role === "ai") {
    bubbleDiv.innerHTML =
      typeof marked !== "undefined"
        ? marked.parse(content)
        : content.replace(/\n/g, "<br>");
  } else {
    bubbleDiv.textContent = content;
  }

  const metaDiv = document.createElement("div");
  metaDiv.className = "message-meta";
  metaDiv.innerHTML = `
        <span class="message-time">${new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}</span>
        ${
          metadata.context
            ? `<span class="context-badge"><i class="fas fa-tag"></i> ${metadata.context}</span>`
            : ""
        }
        ${
          metadata.severity && metadata.severity !== "low"
            ? `<span class="severity-badge ${metadata.severity}"><i class="fas fa-exclamation-circle"></i> ${metadata.severity}</span>`
            : ""
        }
    `;

  contentDiv.appendChild(bubbleDiv);
  if (role === "ai") contentDiv.appendChild(metaDiv);

  messageDiv.appendChild(avatarDiv);
  messageDiv.appendChild(contentDiv);

  chatMessages.appendChild(messageDiv);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Hide quick suggestions after first message
  const suggestions = document.getElementById("quickSuggestions");
  if (suggestions && state.chatHistory.length > 0) {
    suggestions.style.display = "none";
  }
}

function showTypingIndicator() {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) {
    indicator.style.display = "flex";
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight + 100;
  }
  state.isTyping = true;
}

function hideTypingIndicator() {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) indicator.style.display = "none";
  state.isTyping = false;
}

function sendQuickMessage(message) {
  sendChatMessage(message);
}

function quickAction(action) {
  const messages = {
    symptoms: "I want to check my symptoms",
    appointment: "I want to book an appointment",
    medication: "I need medication information",
    emergency: "This is an emergency situation",
  };

  sendChatMessage(messages[action] || action);
}

function exportChat() {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages || state.chatHistory.length === 0) {
    showToast("No chat history to export", "warning");
    return;
  }

  showToast("Generating chat image...", "info");

  lazyLoadHtml2Canvas().then(() => {
    // Deep-clone the chat into a fully-unconstrained off-screen wrapper
    const clone = chatMessages.cloneNode(true);
    const chatWidth = chatMessages.offsetWidth || 600;

    const wrapper = document.createElement("div");
    wrapper.style.cssText = [
      "position:fixed", "left:-9999px", "top:0",
      "width:" + chatWidth + "px", "height:auto", "overflow:visible",
      "background:#f8fafc", "padding:16px", "box-sizing:border-box",
      "font-family:inherit", "z-index:-1",
    ].join(";");

    clone.style.cssText = "height:auto;max-height:none;overflow:visible;padding:8px;";

    const header = document.createElement("div");
    header.style.cssText = [
      "display:flex", "align-items:center", "gap:10px",
      "background:linear-gradient(135deg,#6c63ff,#48cae4)",
      "color:#fff", "font-weight:700", "font-size:15px",
      "padding:12px 18px", "border-radius:12px", "margin-bottom:12px",
    ].join(";");
    header.innerHTML =
      `<span style="font-size:20px;">🏥</span>` +
      `<span>MedicSense AI &nbsp;|&nbsp; Chat Export</span>` +
      `<span style="margin-left:auto;font-weight:400;font-size:12px;opacity:0.88;">${new Date().toLocaleString()}</span>`;

    const footer = document.createElement("div");
    footer.style.cssText = "margin-top:14px;padding:8px 14px;font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;text-align:center;";
    footer.textContent = "⚠️ For health awareness only. Always consult a qualified healthcare professional.";

    wrapper.appendChild(header);
    wrapper.appendChild(clone);
    wrapper.appendChild(footer);
    document.body.appendChild(wrapper);

    requestAnimationFrame(() => {
      html2canvas(wrapper, {
        useCORS: true, allowTaint: true, scale: 2,
        backgroundColor: "#f8fafc", scrollX: 0, scrollY: 0,
        width: wrapper.offsetWidth, height: wrapper.scrollHeight,
        windowWidth: wrapper.offsetWidth, windowHeight: wrapper.scrollHeight,
      })
        .then((canvas) => {
          const link = document.createElement("a");
          link.download = `MedicSense_Chat_${new Date().toISOString().slice(0, 10)}.png`;
          link.href = canvas.toDataURL("image/png");
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          showToast("Chat saved as image ✅", "success");
        })
        .catch((err) => {
          console.error("html2canvas error:", err);
          showToast("Failed to capture screenshot.", "error");
        })
        .finally(() => document.body.removeChild(wrapper));
    });
  }).catch(() => showToast("Could not load screenshot library.", "error"));
}

function clearChat() {
  if (!confirm("Are you sure you want to clear the chat history?")) return;

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
                        <p>Chat history cleared. How can I help you today?</p>
                    </div>
                    <div class="message-meta">
                        <span class="message-time">Just now</span>
                    </div>
                </div>
            </div>
        `;
  }

  state.chatHistory = [];
  saveUserData();

  // Show quick suggestions again
  const suggestions = document.getElementById("quickSuggestions");
  if (suggestions) suggestions.style.display = "flex";

  showToast("Chat history cleared", "success");
}

function toggleChatSettings() {
  showToast("Chat settings coming soon!", "info");
}

// ── Fix 2 & 3 & 4 Frontend: Rich image analysis card + healing tracker ────────

function addImageAnalysisToChat(data, severity, severityIcon, certainty, sanityNote,
                                  visualDesc, conditions, firstAid, warnSigns,
                                  seeDoctor, specialist, healing, doNot) {
  const msgId = `img-analysis-${Date.now()}`;
  const infectionRisk = data.infection_risk || "low";
  const infectionNote = data.infection_note || "";
  const scoringNote   = data.scoring_note   || "";
  const severityScore = data.severity_score != null ? data.severity_score : "";

  // Build checklist items HTML (Fix 2)
  const checklistHTML = firstAid.map((step, i) => `
    <label class="aid-check-item" style="display:flex;align-items:flex-start;gap:8px;margin:4px 0;cursor:pointer;">
      <input type="checkbox" id="aid-${msgId}-${i}" style="margin-top:3px;accent-color:var(--primary,#6c63ff);flex-shrink:0;"
        onchange="this.parentElement.style.opacity=this.checked?'0.5':'1';">
      <span>${step}</span>
    </label>`).join("");

  // Infection risk banner (Fix 4 UI)
  const infectionBanner = infectionRisk === "high" ? `
    <div style="background:#fff3cd;border-left:4px solid #ff9800;padding:8px 12px;border-radius:6px;margin:8px 0;font-size:0.85em;">
      🦠 <strong>Infection Risk: HIGH</strong> — ${infectionNote || "Infection indicators detected. Seek medical attention."}
    </div>` : "";

  // Warning signs
  const warningsHTML = warnSigns.map(w => `<li>${w}</li>`).join("");
  const doNotHTML    = doNot.map(d => `<li style="color:#e74c3c;">${d}</li>`).join("");

  // Delta comparison banner (comparative healing intelligence)
  const delta        = data.delta || "";
  const deltaScore   = data.delta_score || 0;
  const deltaExp     = data.delta_explanation || "";
  const sessionNum   = data.session_number || "";
  const isComparison = data.is_comparison || false;

  // Re-add scoreBadge (previously accidentally removed)
  const scoreBadge = severityScore !== "" ? `<span style="font-size:0.8em;opacity:0.7;margin-left:6px;">Severity score: ${severityScore}/10</span>` : "";

  let deltaBanner = "";
  if (isComparison && delta) {
    const dColor = delta === "improved" ? "#27ae60" : delta === "worsened" ? "#e74c3c" : "#f39c12";
    const dIcon  = delta === "improved" ? "📈" : delta === "worsened" ? "📉" : "➡️";
    const dLabel = delta.charAt(0).toUpperCase() + delta.slice(1);
    // delta_score: -3 to +3. Map to 0-100% bar width where 0=50%.
    const barFill = Math.round(50 + (deltaScore / 3) * 50);
    const barColor = deltaScore >= 0 ? "#27ae60" : "#e74c3c";
    const sign = deltaScore > 0 ? "+" : "";

    deltaBanner = `
    <div style="background:${dColor}18;border:1.5px solid ${dColor};border-radius:10px;padding:12px 14px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:1.3em;">${dIcon}</span>
        <strong style="color:${dColor};font-size:1em;">Healing Progress — Day ${sessionNum}: ${dLabel}</strong>
      </div>
      <div style="font-size:0.85em;margin-bottom:8px;opacity:0.9;">${deltaExp}</div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:0.8em;min-width:80px;">Change score:</span>
        <div style="flex:1;background:#e0e0e0;border-radius:4px;height:8px;overflow:hidden;">
          <div style="width:${barFill}%;background:${barColor};height:100%;border-radius:4px;transition:width 0.6s;"></div>
        </div>
        <span style="font-size:0.85em;font-weight:700;color:${barColor};min-width:40px;">${sign}${deltaScore}</span>
      </div>
    </div>`;
  }

  const html = `
<div style="font-family:inherit;line-height:1.6;">
  <div style="font-weight:700;font-size:1.05em;margin-bottom:6px;">📸 Health Image Analysis — Gemini Vision${sessionNum ? ` (Day ${sessionNum})` : ""}</div>
  ${deltaBanner}

  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
    <span style="font-weight:600;">Identified:</span> ${data.injury_type || "Not identified"} ${severityIcon} ${severity.charAt(0).toUpperCase()+severity.slice(1)} ${scoreBadge}
  </div>
  <div style="font-size:0.82em;opacity:0.65;margin-bottom:8px;">Model certainty (approx.): ${certainty}% — heuristic, not calibrated</div>
  ${sanityNote ? `<div style="font-size:0.8em;background:#e8f4fd;padding:4px 8px;border-radius:4px;margin-bottom:6px;">ℹ️ ${sanityNote}</div>` : ""}
  ${infectionBanner}

  ${visualDesc ? `<div style="margin:8px 0;"><strong>What I See:</strong><br>${visualDesc}</div>` : ""}

  ${conditions.length > 0 ? `<div style="margin:8px 0;"><strong>Possible Conditions:</strong><ol style="margin:4px 0 0 18px;">${conditions.map(c=>`<li>${c}</li>`).join("")}</ol></div>` : ""}

  ${firstAid.length > 0 ? `
  <div style="margin:10px 0;">
    <strong>✅ First Aid Checklist:</strong>
    <div style="margin-top:6px;padding:8px 10px;background:rgba(108,99,255,0.06);border-radius:8px;">
      ${checklistHTML}
    </div>
  </div>` : ""}

  ${warnSigns.length > 0 ? `<div style="margin:8px 0;"><strong>⚠️ Go to ER / Call Doctor If:</strong><ul style="margin:4px 0 0 18px;">${warningsHTML}</ul></div>` : ""}

  ${seeDoctor ? `<div style="margin:6px 0;"><strong>When to See a Doctor:</strong> ${seeDoctor}</div>` : ""}
  ${specialist ? `<div style="margin:4px 0;"><strong>Recommended Specialist:</strong> ${specialist}</div>` : ""}
  ${healing    ? `<div style="margin:4px 0;"><strong>Expected Healing Time:</strong> ${healing}</div>` : ""}

  ${doNot.length > 0 ? `<div style="margin:8px 0;"><strong>🚫 Do NOT:</strong><ul style="margin:4px 0 0 18px;">${doNotHTML}</ul></div>` : ""}

  <div style="margin-top:10px;font-size:0.78em;opacity:0.6;border-top:1px solid rgba(0,0,0,0.1);padding-top:6px;">
    ⚠️ AI analysis — not a medical diagnosis. Always consult a healthcare professional.
  </div>
</div>`;

  // Append as raw HTML message
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) {
    const wrapper = document.createElement("div");
    wrapper.className = "message ai-message";
    wrapper.id = msgId;
    wrapper.style.cssText = "padding:14px 16px;border-radius:16px 16px 16px 4px;max-width:90%;margin:8px 0;";
    wrapper.innerHTML = html;
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

// Fix 3 — Healing Tracker: offer daily photo tracking after injury analysis
function _offerHealingTracker(injuryType) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  const pill = document.createElement("div");
  pill.style.cssText = "display:flex;align-items:center;gap:8px;margin:8px 0;";
  pill.innerHTML = `
    <button onclick="_startHealingTracker('${(injuryType||"injury").replace(/'/g,"\\'")} ')"
      style="display:flex;align-items:center;gap:6px;background:linear-gradient(135deg,#6c63ff,#48cae4);
             color:#fff;border:none;border-radius:20px;padding:8px 16px;cursor:pointer;font-size:0.85em;
             box-shadow:0 2px 8px rgba(108,99,255,0.3);transition:transform 0.15s;"
      onmouseover="this.style.transform='scale(1.04)'" onmouseout="this.style.transform='scale(1)'">
      📅 Track Healing Progress
    </button>
    <span style="font-size:0.8em;opacity:0.6;">Upload a photo each day to monitor recovery</span>
  `;
  chatMessages.appendChild(pill);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function _startHealingTracker(injuryType) {
  // Set tracker state
  if (!window.state) window.state = {};
  window.state.healingTrackerActive = true;
  window.state.healingTrackerInjury = injuryType;
  window.state.healingTrackerDay    = (window.state.healingTrackerDay || 0) + 1;

  const day = window.state.healingTrackerDay;
  const msg = day === 1
    ? `📅 **Healing Tracker Started** for: _${injuryType}_\n\nGreat! Upload a photo each day and I'll compare your healing progress. Use the 📎 button to upload today's photo (Day ${day}).`
    : `📅 **Healing Tracker — Day ${day}** for: _${injuryType}_\n\nUpload today's photo using the 📎 button and I'll assess how your healing has progressed since Day ${day - 1}.`;

  addMessageToChat("ai", msg, { context: "healing-tracker" });
}

function attachFile() {
  document.getElementById("chatFileInput")?.click();
}

async function handleChatImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validate file
  if (!CONFIG.SUPPORTED_FORMATS.includes(file.type)) {
    showToast("Please upload a valid image (JPG, PNG, or WEBP)", "warning");
    return;
  }

  if (file.size > CONFIG.MAX_FILE_SIZE) {
    showToast("Image size must be less than 10MB", "warning");
    return;
  }

  showToast("Analyzing image with Gemini AI...", "info");

  try {
    // Convert image to base64
    const reader = new FileReader();
    reader.onload = async function (e) {
      const imageDataUrl = e.target.result;

      // Add user message showing image was uploaded
      addMessageToChat("user", "📸 [Image uploaded for analysis]", {
        context: "image-upload",
        image: imageDataUrl,
      });

      // Show typing indicator
      showTypingIndicator();

      try {
        // Call backend API with Gemini for disease recognition
        const response = await fetchWithTimeout(
          `${CONFIG.API_BASE_URL}/analyze-injury-image`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              image: imageDataUrl,
              user_id: state.userId || state.user?.uid || "anonymous",
              notes: "Analyze this health image and provide detailed insights.",
              tracking_session: !!(window.state?.healingTrackerActive),
            }),
          },
          30000   // 30s — comparison calls are slower
        );

        const data = await response.json();

        hideTypingIndicator();

        if (data.success) {
          const injuryType = data.injury_type || "Not identified";
          const severity   = data.severity    || "unknown";
          const certainty  = data.model_certainty_approx ?? data.confidence ?? 0;
          const sanityNote = data.sanity_note || "";

          const visualDesc = data.visual_description || data.description || "No visual description available.";
          const firstAid   = data.immediate_first_aid || data.cure_steps || [];
          const warnSigns  = data.warning_signs || [];
          const seeDoctor  = data.see_doctor_if || data.medical_advice || "";
          const specialist = data.recommended_specialist || "";
          const healing    = data.healing_time || "";
          const conditions = data.possible_conditions || data.disease_characteristics || [];
          const doNot      = data.do_not || [];

          const severityIcon = severity === "emergency" ? "🚨"
                             : severity === "severe"    ? "🔴"
                             : severity === "moderate"  ? "🟡" : "🟢";

          // Render rich HTML checklist card
          addImageAnalysisToChat(data, severity, severityIcon, certainty, sanityNote,
                                  visualDesc, conditions, firstAid, warnSigns,
                                  seeDoctor, specialist, healing, doNot);

          // Offer healing tracker after short delay
          setTimeout(() => _offerHealingTracker(data.injury_type), 1200);

          showToast("Image analyzed with Gemini Vision AI!", "success");

        } else {
          // Show the actual error from backend, not a generic message
          const errMsg = data.error || data.message || "Analysis failed.";
          const errCode = data.code || "";
          console.error("Image analysis error:", data);

          let friendlyMsg = `❌ ${errMsg}`;
          if (errCode === "NON_MEDICAL_IMAGE") {
            friendlyMsg = `🚫 ${errMsg}`;
          } else if (response.status === 429) {
            const retry = data.retry_after_seconds;
            friendlyMsg = `⏳ ${errMsg}${retry ? ` (retry in ${retry}s)` : ""}`;
          } else if (response.status === 413) {
            friendlyMsg = `📦 ${errMsg}`;
          } else if (response.status === 415) {
            friendlyMsg = `🖼️ ${errMsg}`;
          }
          addMessageToChat("ai", friendlyMsg, { context: "error" });
        }
      } catch (error) {
        hideTypingIndicator();
        console.error("Error analyzing image:", error);
        addMessageToChat(
          "ai",
          "❌ Sorry, I encountered an error analyzing the image. Please try again.",
          {
            context: "error",
          }
        );
        showToast("Error analyzing image. Please try again.", "error");
      }
    };

    reader.readAsDataURL(file);
  } catch (error) {
    console.error("Error processing image:", error);
    showToast("Error processing image. Please try again.", "error");
  }
}

function toggleVoiceInput() {
  useVoiceInput("chat");
}

// ========================================
// EMERGENCY FUNCTIONS
// ========================================
function handleEmergency() {
  const modal = document.getElementById("emergencyModal");
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeEmergencyModal() {
  const modal = document.getElementById("emergencyModal");
  if (modal) {
    modal.style.display = "none";
  }
}

function emergencyChat() {
  closeEmergencyModal();
  scrollToSection("ai-chat");

  // Generate session ID for emergency tracking
  const sessionId =
    Date.now().toString() + "_" + Math.random().toString(36).substr(2, 9);

  setTimeout(() => {
    // BACKEND EMERGENCY MODE: Activate strict emergency context
    const emergencyMessage = "I need urgent help!";

    fetch("http://localhost:5000/api/emergency/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: emergencyMessage,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Display strict emergency response from backend
          displayChatMessage(data.response, "ai");

          // Visual indicator for emergency mode
          if (data.emergency_mode) {
            showToast(
              "⚠️ EMERGENCY MODE: Call 112 immediately",
              "error",
              10000
            );
          }
        } else {
          // Fallback if backend fails
          displayChatMessage(
            "🚨 CALL 112 IMMEDIATELY\n\n" +
              "System error occurred. Emergency services must be contacted directly. " +
              "Do NOT rely on AI in emergency situations.",
            "ai"
          );
        }
      })
      .catch((error) => {
        console.error("Emergency chat error:", error);
        // Critical fallback
        displayChatMessage(
          "🚨 CALL 112 IMMEDIATELY\n\n" +
            "System unavailable. Contact emergency services now. " +
            "This is NOT a substitute for professional help.",
          "ai"
        );
      });
  }, 500);
}

function findNearestHospital() {
  const fallbackUrl =
    "https://www.google.com/maps/search/emergency+room+near+me/";

  if (!("geolocation" in navigator)) {
    window.open(fallbackUrl, "_blank");
    showToast("Opening map search (Location not supported)", "warning");
    return;
  }

  showToast("Locating nearest emergency rooms...", "info");

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;

      // Try backend hospital lookup first
      fetch("http://localhost:5000/api/emergency/hospitals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude, longitude }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (
            data.status === "fallback" ||
            data.action === "redirect_to_maps"
          ) {
            // Backend returned safe fallback - use Google Maps
            const mapsUrl =
              data.fallback_url ||
              `https://www.google.com/maps/search/emergency+room/@${latitude},${longitude},15z`;
            window.open(mapsUrl, "_blank");
            showToast(data.message || "Opening emergency room search", "info");
          } else {
            // Backend provided real hospital data (future implementation)
            window.open(
              `https://www.google.com/maps/search/emergency+room/@${latitude},${longitude},15z`,
              "_blank"
            );
            showToast("Found nearest emergency centers", "success");
          }
        })
        .catch((error) => {
          console.error("Hospital lookup error:", error);
          // Safe fallback on error
          const mapsUrl = `https://www.google.com/maps/search/emergency+room/@${latitude},${longitude},15z`;
          window.open(mapsUrl, "_blank");
          showToast("Opening emergency room search", "info");
        });
    },
    (error) => {
      console.error("Geolocation error:", error);
      window.open(fallbackUrl, "_blank");
      showToast("Location unavailable, opening map search", "warning");
    }
  );
}

// Handler for Call Button (to be attached via listener)
function handleEmergencyCall(e) {
  // Log emergency escalation to backend
  const sessionId =
    Date.now().toString() + "_" + Math.random().toString(36).substr(2, 9);

  navigator.geolocation.getCurrentPosition(
    (position) => {
      fetch("http://localhost:5000/api/emergency/escalate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:
            state.currentUser ||
            "guest_" + Math.random().toString(36).substr(2, 9),
          session_id: sessionId,
          location: {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          },
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            console.log("Emergency escalation logged:", data.emergency_id);
          }
        })
        .catch((error) => {
          console.error("Emergency logging error:", error);
        });
    },
    (error) => {
      // Log without location if unavailable
      fetch("http://localhost:5000/api/emergency/escalate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:
            state.currentUser ||
            "guest_" + Math.random().toString(36).substr(2, 9),
          session_id: sessionId,
          location: null,
        }),
      }).catch((err) => console.error("Emergency logging error:", err));
    }
  );

  // Show toast for desktop users
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  if (!isMobile) {
    showToast("Dial 112 on your phone immediately", "info");
  }
}

// ========================================
// HEALTH TRACKING FUNCTIONS
// ========================================
function viewHealthDetails() {
  showToast("Detailed health analytics coming soon!", "info");
}

// ========================================
// UTILITY FUNCTIONS
// ========================================
function showToast(message, type = "info") {
  // Create toast element
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icon =
    {
      success: "check-circle",
      error: "exclamation-circle",
      warning: "exclamation-triangle",
      info: "info-circle",
    }[type] || "info-circle";

  toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;

  // Add to body
  document.body.appendChild(toast);

  // Animate in
  setTimeout(() => toast.classList.add("show"), 10);

  // Remove after 4 seconds
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

function validatePhone(phone) {
  // Remove all non-digit characters for counting
  const digitsOnly = phone.replace(/\D/g, "");

  // Basic sanity check: 7-15 digits (supports international formats)
  // Allows: +, -, spaces, parentheses, digits
  const re = /^[\d\s\-\+\(\)]+$/;
  return re.test(phone) && digitsOnly.length >= 7 && digitsOnly.length <= 15;
}

function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ========================================
// LOCAL STORAGE FUNCTIONS
// ========================================
function saveUserData() {
  try {
    localStorage.setItem("medicsense_user_id", state.currentUser);
    localStorage.setItem(
      "medicsense_chat_history",
      JSON.stringify(state.chatHistory)
    );
    localStorage.setItem(
      "medicsense_appointments",
      JSON.stringify(state.appointments)
    );
    localStorage.setItem("medicsense_symptoms", JSON.stringify(state.symptoms));
  } catch (error) {
    console.error("Error saving user data:", error);
  }
}

function loadUserData() {
  try {
    const savedUserId = localStorage.getItem("medicsense_user_id");
    if (savedUserId) state.currentUser = savedUserId;

    // Ensure we never run with a null/empty user id
    state.currentUser = resolveUserId();

    // ── Improvement 1: Restore chat history to UI ──────────────────────
    const savedChatHistory = localStorage.getItem("medicsense_chat_history");
    if (savedChatHistory) {
      const history = JSON.parse(savedChatHistory);
      state.chatHistory = history;
      if (history.length > 0) {
        _restoreChatHistoryToUI(history);
      }
    }

    const savedAppointments = localStorage.getItem("medicsense_appointments");
    if (savedAppointments) {
      state.appointments = JSON.parse(savedAppointments);
      updateAppointmentsList();
    }

    const savedSymptoms = localStorage.getItem("medicsense_symptoms");
    if (savedSymptoms) state.symptoms = JSON.parse(savedSymptoms);

    console.log("📦 User data loaded from localStorage");
  } catch (error) {
    console.error("Error loading user data:", error);
  }
}

// Render saved chat messages into the chat UI on page load
function _restoreChatHistoryToUI(history) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  // Keep the initial welcome message that's baked into the HTML
  // Just append restored messages after it
  const MAX_RESTORE = 50; // Don't restore more than 50 messages to keep UI snappy
  const slice = history.slice(-MAX_RESTORE);

  slice.forEach((msg) => {
    addMessageToChat(msg.role, msg.content, msg.metadata || {});
  });

  // Show a subtle "restored" badge
  const badge = document.createElement("div");
  badge.style.cssText = [
    "text-align:center",
    "font-size:0.72rem",
    "color:#9ca3af",
    "padding:4px 0 8px",
    "border-top:1px dashed #e5e7eb",
    "margin:4px 0",
  ].join(";");
  badge.textContent = `💾 ${slice.length} message${slice.length !== 1 ? 's' : ''} restored from your last session`;
  chatMessages.insertBefore(badge, chatMessages.firstChild.nextSibling);
  setTimeout(() => badge.remove(), 5000); // Fade out after 5s

  // Hide quick suggestions since there's already a conversation
  const suggestions = document.getElementById("quickSuggestions");
  if (suggestions) suggestions.style.display = "none";
}

// ========================================
// USER ID RESOLUTION (PRODUCTION-GRADE)
// ========================================
function resolveUserId() {
  // 1) Authenticated Global (Primary)
  if (AUTHENTICATED_USER && AUTHENTICATED_USER.uid) {
    return AUTHENTICATED_USER.uid;
  }

  // 2) Firebase auth state
  if (state && state.currentUser) {
    return String(state.currentUser);
  }

  // 3) localStorage (correct key)
  try {
    const saved = localStorage.getItem("medicsense_authenticated_user");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.uid) return parsed.uid;
    }
  } catch (_) {}

  // 4) Legacy fallback
  try {
    const savedUserObj = localStorage.getItem("medicsense_user");
    if (savedUserObj) {
      const parsed = JSON.parse(savedUserObj);
      const id =
        parsed && (parsed.id || parsed.user_id || parsed.userId || parsed.uid);
      if (id) {
        localStorage.setItem("medicsense_user_id", String(id));
        return String(id);
      }
    }
  } catch (_) {}

  // 3) persisted id
  const persisted = localStorage.getItem("medicsense_user_id");
  if (persisted && persisted !== "null" && persisted !== "undefined") {
    return String(persisted);
  }

  // 4) generate stable guest id (saved so it remains consistent)
  const guestId = `guest_${Math.random()
    .toString(36)
    .slice(2, 10)}${Date.now().toString(36)}`;
  localStorage.setItem("medicsense_user_id", guestId);
  return guestId;
}

function getUserId() {
  const userId = resolveUserId();
  // keep state in sync for existing calls
  state.currentUser = userId;
  return userId;
}

// ========================================
// AUTHENTICATION FUNCTIONS (Production Ready)
// ========================================

// Store original modal content once at page load
let originalAuthModalContent = null;

function initAuthModal() {
  const modal = document.getElementById("authModal");
  const modalContent = modal?.querySelector(".auth-modal");
  if (modalContent && !originalAuthModalContent) {
    originalAuthModalContent = modalContent.innerHTML;
    console.log("✅ Original auth modal content saved");
  }
}

function openAuthModal() {
  // CRITICAL: Only show modal if user is NOT authenticated
  if (!shouldShowAuthModal()) {
    console.log("ℹ️ User already authenticated - not showing auth modal");
    return;
  }

  // CRITICAL: Don't reopen if it was just closed by successful login
  if (AUTH_MODAL_CLOSED_BY_LOGIN) {
    console.log("ℹ️ Modal was just closed by login - not reopening");
    return;
  }

  const modal = document.getElementById("authModal");
  if (modal) {
    modal.style.display = "flex";
    document.body.style.overflow = "hidden"; // Prevent background scroll
    console.log("📖 Auth modal opened");
  }
}

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) {
    // CRITICAL: Set flag that modal was closed by login
    AUTH_MODAL_CLOSED_BY_LOGIN = true;

    // CRITICAL: REMOVE the modal from DOM entirely, not just hide it
    // This prevents re-render bugs
    modal.style.display = "none";
    document.body.style.overflow = ""; // Restore scroll
    console.log(
      "📕 Modal closed - Auth state:",
      AUTHENTICATED_USER ? "Authenticated" : "Not authenticated"
    );

    // Reset flag after 2 seconds to allow manual opening later
    setTimeout(() => {
      AUTH_MODAL_CLOSED_BY_LOGIN = false;
      console.log("🔄 Modal can be manually opened again");
    }, 2000);
  }
}

function restoreAuthModal() {
  const modal = document.getElementById("authModal");
  const modalContent = modal?.querySelector(".auth-modal");

  if (modalContent && originalAuthModalContent) {
    modalContent.innerHTML = originalAuthModalContent;
    // CRITICAL: Ensure modal stays hidden after restore
    if (modal) {
      modal.style.display = "none";
    }
    console.log("✅ Auth modal restored to original state (hidden)");
  }
}

async function handleEmailLogin() {
  // GOOGLE-ONLY AUTH: Email/password authentication has been removed
  // This button now triggers Google Sign-In directly
  console.log("Email/password auth disabled - redirecting to Google Sign-In");
  await handleGoogleLogin();
}

async function handleGoogleLogin() {
  console.log("🔐 Google Sign-In initiated");

  if (!window.firebaseAuth) {
    console.error("❌ Firebase not initialized");
    showToast("System initializing... please wait.", "warning");
    return;
  }

  const { auth, signInWithPopup, GoogleAuthProvider } = window.firebaseAuth;
  const provider = new GoogleAuthProvider();

  console.log("✅ Firebase auth available:", !!auth);
  console.log("✅ GoogleAuthProvider available:", !!GoogleAuthProvider);

  try {
    setAuthLoading(true);
    console.log("🔄 Opening Google Sign-In popup...");

    const result = await signInWithPopup(auth, provider);

    console.log("✅ Sign-In successful!");
    console.log("👤 User:", result.user?.email);

    // Don't close modal or show toast here - onAuthStateChanged will handle it
  } catch (error) {
    setAuthLoading(false);
    console.error("❌ LOGIN ERROR:", error);
    console.error("Error code:", error.code);
    console.error("Error message:", error.message);

    if (error.code === "auth/popup-closed-by-user") {
      console.log("ℹ️ User cancelled sign-in popup");
      // Don't show toast - user intentionally cancelled
    } else if (error.code === "auth/network-request-failed") {
      showAuthError("No internet connection. Please check your network.");
    } else if (error.code === "auth/unauthorized-domain") {
      showAuthError(
        "This domain is not authorized. Quick Fix: Access the site via http://localhost:8001 instead of your IP address. Otherwise, add this domain in Firebase Console > Authentication > Settings > Authorized domains."
      );
    } else if (error.code === "auth/popup-blocked") {
      showAuthError(
        "Popup was blocked by browser. Please allow popups for this site."
      );
    } else {
      showAuthError("Sign-In failed: " + error.message);
    }
  }
}

function updateAuthUI(user) {
  const authBtn = document.getElementById("authBtn");
  if (!authBtn) return;

  if (user && AUTHENTICATED_USER) {
    // User is authenticated - show profile picture
    const name = getSafeName(user);
    const email = getSafeEmail(user);
    const photoURL = getSafePhotoURL(user);

    const fallbackURL = getAvatarFallbackURL(name, email);
    authBtn.innerHTML = `<img src="${photoURL}" alt="${name}" referrerpolicy="no-referrer" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover;" onerror="this.onerror=null;this.src='${fallbackURL}'">`;
    authBtn.title = `Signed in as ${email}`;
    authBtn.onclick = () => showProfileModal(user);
  } else {
    // User is NOT authenticated - show login button
    authBtn.innerHTML = '<i class="fas fa-user-circle"></i>';
    authBtn.title = "Sign In";
    authBtn.onclick = openAuthModal;
  }
}

function showProfileModal(user) {
  const modal = document.getElementById("authModal");
  const modalContent = modal?.querySelector(".auth-modal");

  if (!modalContent) {
    console.error("❌ Auth modal content not found");
    return;
  }

  const name = getSafeName(user);
  const email = getSafeEmail(user);
  const photoURL = getSafePhotoURL(user);

  const fallbackModalURL = getAvatarFallbackURL(name, email);
  modalContent.innerHTML = `
        <button class="modal-close" onclick="closeAuthModal()">
            <i class="fas fa-times"></i>
        </button>
        <div class="auth-header" style="text-align: center;">
            <img src="${photoURL}" alt="Profile" referrerpolicy="no-referrer" style="width: 80px; height: 80px; border-radius: 50%; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); object-fit: cover;" onerror="this.onerror=null;this.src='${fallbackModalURL}'">
            <h3 style="margin-bottom: 5px; color: #1e293b;">${name}</h3>
            <p style="color: #64748b; margin: 0;">${email}</p>
        </div>

        <div class="auth-options">
            <button id="btnSignOut" class="auth-btn-google" onclick="handleLogout()" style="justify-content: center; background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; font-weight: 500;">
                <i class="fas fa-sign-out-alt"></i>
                <span>Sign Out</span>
            </button>
        </div>

        <div style="margin-top: 20px; text-align: center;">
            <p style="font-size: 0.8rem; color: #cbd5e1;">MedicSense AI • Secure Session</p>
        </div>
    `;

  openAuthModal();
}

async function handleLogout() {
  const btn = document.getElementById("btnSignOut");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML =
      '<i class="fas fa-circle-notch fa-spin"></i> <span>Signing out...</span>';
    btn.style.opacity = "0.7";
  }

  try {
    if (window.firebaseAuth) {
      await window.firebaseAuth.signOut(window.firebaseAuth.auth);
    }

    // CLEAR ALL STATE - CRITICAL FOR SECURITY
    clearAuthState(); // Use our new centralized function
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

    await new Promise((r) => setTimeout(r, 500));

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

    // Restore auth modal to original login state (but don't show it)
    restoreAuthModal();
    closeAuthModal();
    showToast("Successfully signed out", "success");
  } catch (error) {
    console.error("LOGOUT ERROR", error);
    showToast("Error signing out: " + error.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML =
        '<i class="fas fa-sign-out-alt"></i> <span>Sign Out</span>';
      btn.style.opacity = "1";
    }
  }
}

function getReadableAuthError(error) {
  const map = {
    "auth/invalid-email": "Please enter a valid email address",
    "auth/wrong-password":
      "Unable to sign in. Please check your credentials and try again.",
    "auth/weak-password": "Password must be at least 6 characters",
    "auth/too-many-requests": "Too many attempts. Please try again later.",
    "auth/network-request-failed":
      "Connection issue. Please check your network and try again.",
    "auth/user-disabled":
      "This account is currently unavailable. Please contact support.",
    "auth/operation-not-allowed": "This sign-in method is not available.",
  };
  return map[error.code] || "Unable to complete sign-in. Please try again.";
}

function setAuthLoading(isLoading) {
  const btnGoogle = document.getElementById("btnGoogle");
  const btnEmail = document.getElementById("btnEmailLogin");

  const toggle = (el, disabled, opacity) => {
    if (el) {
      el.disabled = disabled;
      el.style.opacity = opacity;
    }
  };

  if (isLoading) {
    toggle(btnGoogle, true, "0.5");
    if (btnEmail) {
      btnEmail.disabled = true;
      btnEmail.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
      btnEmail.style.opacity = "0.7";
    }
  } else {
    toggle(btnGoogle, false, "1");
    if (btnEmail) {
      btnEmail.disabled = false;
      btnEmail.innerHTML = "Sign In / Sign Up";
      btnEmail.style.opacity = "1";
    }
  }
}

function showAuthError(message) {
  const errorDiv = document.getElementById("authError");
  if (errorDiv) {
    errorDiv.style.display = "block";
    errorDiv.textContent = message;
  }
  showToast(message, "error");
}

// Close auth modal on outside click - BUT ONLY IF USER IS NOT AUTHENTICATED
document.addEventListener("click", function (event) {
  const authModal = document.getElementById("authModal");
  if (authModal && event.target === authModal) {
    // Only allow closing if user is not authenticated or already logged in
    if (!AUTHENTICATED_USER || authModal.style.display === "flex") {
      closeAuthModal();
    }
  }
});

// ========================================
// AUTOMATIC LOCATION DETECTION
// ========================================
function detectUserLocation() {
  const locationElement = document.getElementById("user-location");

  if (!locationElement) return;

  // Try to get user's location using Geolocation API
  if ("geolocation" in navigator) {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;

        try {
          // Use reverse geocoding to get city/country
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`
          );
          const data = await response.json();

          const city =
            data.address.city ||
            data.address.town ||
            data.address.village ||
            "";
          const state = data.address.state || "";
          const country = data.address.country || "";

          let locationText = "";
          if (city && country) {
            locationText = `${city}, ${state ? state + ", " : ""}${country}`;
          } else if (country) {
            locationText = country;
          } else {
            locationText = "Location detected";
          }

          locationElement.textContent = locationText;
          console.log("✅ Location detected:", locationText);
        } catch (error) {
          console.warn("⚠️ Could not fetch location details:", error);
          locationElement.textContent = "Healthcare District, India";
        }
      },
      (error) => {
        console.warn("⚠️ Geolocation error:", error.message);
        locationElement.textContent = "Healthcare District, India";
      },
      {
        enableHighAccuracy: false,
        timeout: 5000,
        maximumAge: 0,
      }
    );
  } else {
    locationElement.textContent = "Healthcare District, India";
  }
}

// Initialize location detection when page loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", detectUserLocation);
} else {
  detectUserLocation();
}

// ========================================
// OPEN LIVE LOCATION ON GOOGLE MAPS
// ========================================
function openLiveLocation() {
  if (navigator.geolocation) {
    // Show loading message
    const locationSpan = document.getElementById("user-location");
    const originalText = locationSpan.textContent;
    locationSpan.textContent = "Getting your location...";

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        // Open Google Maps with the coordinates
        const mapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
        window.open(mapsUrl, "_blank");

        // Restore original text
        locationSpan.textContent = originalText;
      },
      (error) => {
        console.warn("⚠️ Error getting precise location:", error.message);

        // Second attempt: Try again with lower accuracy requirements
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const mapsUrl = `https://www.google.com/maps?q=${pos.coords.latitude},${pos.coords.longitude}`;
                window.open(mapsUrl, "_blank");
                locationSpan.textContent = originalText;
            },
            (err) => {
                console.error("❌ Fallback location also failed:", err);
                // Fallback: Open Google Maps to Greater Noida, Uttar Pradesh, India
                const fallbackUrl = "https://www.google.com/maps/place/Greater+Noida,+Uttar+Pradesh,+India";
                window.open(fallbackUrl, "_blank");
                locationSpan.textContent = originalText;
                alert("Could not get your precise location. Opening our office location instead.");
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
        );
      },
      {
        enableHighAccuracy: true,
        timeout: 8000, // Increased timeout
        maximumAge: 0,
      }
    );
  } else {
    // Geolocation not supported - open default location
    const fallbackUrl =
      "https://www.google.com/maps/place/Greater+Noida,+Uttar+Pradesh,+India";
    window.open(fallbackUrl, "_blank");
    alert(
      "Geolocation is not supported by your browser. Opening our office location."
    );
  }
}

// ========================================
// EXPORT FOR DEBUGGING
// ========================================
if (typeof window !== "undefined") {
  window.MedicSenseAI = {
    state,
    config: CONFIG,
    functions: {
      analyzeSymptoms,
      bookAppointment,
      sendChatMessage,
      handleEmergency,
    },
  };
}

// Keyboard accessibility - Close modals on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    // Close auth modal if open
    const authModal = document.getElementById("authModal");
    if (authModal && authModal.style.display === "flex") {
      closeAuthModal();
    }

    // Close emergency modal if open
    const emergencyModal = document.getElementById("emergencyModal");
    if (emergencyModal && emergencyModal.style.display === "flex") {
      closeEmergencyModal();
    }
  }
});

console.log(
  "✅ MedicSense AI Ultra - Ready to solve healthcare automation challenges!"
);

// Initialize symptom input validation and notification polling when page loads
const initializeApp = () => {
  setupSymptomInputValidation();

  // Re-enable notification polling (Every 30 seconds)
  console.log("🔔 Starting notification poll...");
  fetchNotifications(); // Initial fetch
  setInterval(fetchNotifications, 30000);

  // Reload appointments when window regains focus
  window.addEventListener("focus", () => {
    console.log(
      "🔄 Window focused - refreshing appointments and notifications..."
    );
    const savedAppointments = localStorage.getItem("medicsense_appointments");
    if (savedAppointments) {
      state.appointments = JSON.parse(savedAppointments);
      updateAppointmentsList();
    }
    // Also refresh notification badge
    loadNotificationCountSafe();
  });
};

// --- Dark Mode Logic ---
function toggleDarkMode() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const isDark = currentTheme !== 'dark';

  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  document.documentElement.classList.toggle('dark-mode', isDark);
  document.body.classList.toggle('dark-mode', isDark);

  const newValue = isDark ? '1' : '0';
  localStorage.setItem('medicsense_dark_mode', newValue);

  const icon = document.getElementById('darkModeIcon');
  if (icon) {
    icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
  }
}

// Restore dark mode preference
(function() {
  const isDark = localStorage.getItem('medicsense_dark_mode') === '1';
  if (isDark) {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.documentElement.classList.add('dark-mode');
    document.body.classList.add('dark-mode');
    setTimeout(() => {
      const icon = document.getElementById('darkModeIcon');
      if (icon) {
        icon.className = 'fas fa-sun';
      }
    }, 100);
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
    document.documentElement.classList.remove('dark-mode');
  }
})();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}
