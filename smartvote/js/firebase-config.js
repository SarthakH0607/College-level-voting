// ============================================================
// SmartVote — Firebase Configuration (Compat SDK)
// DO NOT wrap in <script> tags — this is loaded as a .js file
// ============================================================

const firebaseConfig = {
  apiKey: "AIzaSyAytwaAipErCT-xV20H7YPLRtC_N5QQ_uw",
  authDomain: "college-level-voting.firebaseapp.com",
  projectId: "college-level-voting",
  storageBucket: "college-level-voting.firebasestorage.app",
  messagingSenderId: "716064018049",
  appId: "1:716064018049:web:d8b639f45daf84cf3a4780",
  measurementId: "G-CKM59H7B80"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Service references
const auth = firebase.auth();
const db = firebase.firestore();
const storage = firebase.storage();

// Google Auth Provider
const googleProvider = new firebase.auth.GoogleAuthProvider();

console.log('%c🗳️ SmartVote Firebase Initialized', 'color: #2563eb; font-weight: bold; font-size: 14px;');
