import 'dart:async';
import 'package:flutter/widgets.dart';
import 'auth_service.dart';
import 'logger_service.dart';

/// Manages automatic token refresh based on user activity
/// - Monitors user interactions (taps, scrolls, etc.)
/// - Refreshes token before expiration when user is active
/// - Stops refreshing after prolonged inactivity
class TokenRefreshManager {
  static final TokenRefreshManager _instance = TokenRefreshManager._internal();
  factory TokenRefreshManager() => _instance;
  TokenRefreshManager._internal();

  final AuthService _authService = AuthService();
  final LoggerService _logger = LoggerService();

  Timer? _refreshTimer;
  DateTime _lastActivity = DateTime.now();
  bool _isInitialized = false;

  // Configuration
  static const Duration checkInterval = Duration(minutes: 5); // Check every 5 min
  static const Duration inactivityThreshold = Duration(minutes: 15); // Stop after 15 min idle
  static const int tokenRefreshThreshold = 20; // Refresh when token is 20+ min old

  /// Initialize the token refresh manager
  void initialize() {
    if (_isInitialized) return;
    
    _isInitialized = true;
    _lastActivity = DateTime.now();
    
    // Start periodic check
    _refreshTimer = Timer.periodic(checkInterval, (_) => _checkAndRefresh());
    
    _logger.info('🔄 Token refresh manager initialized');
  }

  /// Record user activity
  void recordActivity() {
    _lastActivity = DateTime.now();
  }

  /// Check if token needs refresh and do it if user is active
  Future<void> _checkAndRefresh() async {
    try {
      // Check if user is still logged in
      final isLoggedIn = await _authService.isLoggedIn();
      if (!isLoggedIn) {
        _logger.info('⏸️  Not logged in - skipping token refresh');
        return;
      }

      // Check if user has been inactive too long
      final timeSinceActivity = DateTime.now().difference(_lastActivity);
      if (timeSinceActivity > inactivityThreshold) {
        _logger.info('💤 User inactive for ${timeSinceActivity.inMinutes} min - skipping refresh');
        return;
      }

      // Check if token is old enough to refresh
      final shouldRefresh = await _authService.shouldRefreshToken();
      if (!shouldRefresh) {
        _logger.info('✅ Token still fresh - no refresh needed');
        return;
      }

      // Token is old and user is active - refresh it
      final tokenAge = await _authService.getTokenAgeMinutes();
      _logger.info('🔄 Token is $tokenAge min old, user is active - refreshing...');
      
      final success = await _authService.refreshToken();
      if (success) {
        _logger.success('✅ Auto-refreshed token successfully');
      } else {
        _logger.error('❌ Auto-refresh failed - user may need to re-login');
      }
    } catch (e) {
      _logger.error('❌ Token refresh check error: $e');
    }
  }

  /// Manually trigger a token refresh
  Future<bool> refreshNow() async {
    _logger.info('🔄 Manual token refresh triggered');
    return await _authService.refreshToken();
  }

  /// Dispose resources
  void dispose() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    _isInitialized = false;
    _logger.info('🛑 Token refresh manager disposed');
  }
}

/// Widget that monitors user activity for token refresh
class ActivityMonitor extends StatefulWidget {
  final Widget child;

  const ActivityMonitor({Key? key, required this.child}) : super(key: key);

  @override
  State<ActivityMonitor> createState() => _ActivityMonitorState();
}

class _ActivityMonitorState extends State<ActivityMonitor> {
  final TokenRefreshManager _refreshManager = TokenRefreshManager();

  @override
  void initState() {
    super.initState();
    _refreshManager.initialize();
  }

  @override
  void dispose() {
    // Don't dispose the singleton, just stop tracking
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (_) => _refreshManager.recordActivity(),
      onPointerMove: (_) => _refreshManager.recordActivity(),
      child: widget.child,
    );
  }
}
