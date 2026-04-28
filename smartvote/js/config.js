// ============================================================
// SmartVote — Application Configuration
// ============================================================

const APP_CONFIG = {
  appName: 'SmartVote',
  collegeName: 'City College of Technology',
  version: '1.0.0',

  // Biometric microservice URL
  biometricServiceURL: 'http://localhost:4000',

  // Max biometric retry attempts before lockout
  maxBiometricRetries: 3,

  // Admin access key for registration
  adminAccessKey: 'SMARTVOTE_ADMIN_2025',

  // Passphrase pool for voice verification
  voicePassphrases: [
    'SmartVote Secure 2025',
    'My voice is my password',
    'College election verification',
    'I authorize this vote today',
    'Digital democracy secure access',
    'Verify my identity now',
    'SmartVote biometric access',
    'Secure voting platform login'
  ],

  // Role page access map
  roleAccess: {
    'index.html':              ['student'],
    'vote.html':               ['student'],
    'teacher-dashboard.html':  ['teacher'],
    'teacher-vote.html':       ['teacher'],
    'results.html':            ['student', 'teacher'],
    'profile.html':            ['student', 'teacher'],
    'admin.html':              ['admin'],
    'confirmation.html':       ['student', 'teacher'],
    'about.html':              ['student', 'teacher', 'admin'],
    'features.html':           ['student', 'teacher', 'admin']
  },

  // Role → dashboard redirect
  roleDashboard: {
    student: 'index.html',
    teacher: 'teacher-dashboard.html',
    admin:   'admin.html'
  },

  // Random passphrase generator
  getRandomPassphrase() {
    return this.voicePassphrases[Math.floor(Math.random() * this.voicePassphrases.length)];
  }
};
