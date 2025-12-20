// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-analytics.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyDYafuD9h41VWV6TdlTUqvcAmoeNeiOO9s",
    authDomain: "medisenceai.firebaseapp.com",
    projectId: "medisenceai",
    storageBucket: "medisenceai.firebasestorage.app",
    messagingSenderId: "894203517434",
    appId: "1:894203517434:web:2cd12e3453322ee59e6c43",
    measurementId: "G-932YNSBXPC"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

export { auth, googleProvider, signInWithPopup, signOut, onAuthStateChanged };
