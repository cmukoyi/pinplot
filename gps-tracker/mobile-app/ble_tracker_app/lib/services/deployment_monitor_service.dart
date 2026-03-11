import 'dart:async';
import 'package:flutter/foundation.dart';

class DeploymentMonitorService {
  static final DeploymentMonitorService _instance = DeploymentMonitorService._internal();

  factory DeploymentMonitorService() {
    return _instance;
  }

  DeploymentMonitorService._internal();

  bool _isDeploying = false;
  Timer? _healthCheckTimer;
  final Duration _checkInterval = Duration(seconds: 3);
  final Duration _maxWaitTime = Duration(minutes: 10);
  DateTime? _deploymentStartTime;

  final _deploymentStateChanged = StreamController<bool>.broadcast();

  bool get isDeploying => _isDeploying;
  Stream<bool> get deploymentStateChanged => _deploymentStateChanged.stream;

  /// Called when a deployment error is detected
  void detectDeploymentInProgress() {
    if (!_isDeploying) {
      _isDeploying = true;
      _deploymentStartTime = DateTime.now();
      _deploymentStateChanged.add(true);
      _startHealthChecks();
    }
  }

  /// Check if error indicates deployment in progress
  static bool isDeploymentError(dynamic error) {
    final errorStr = error.toString().toLowerCase();
    return (errorStr.contains('html') ||
        errorStr.contains('syntax') ||
        errorStr.contains('<html') ||
        errorStr.contains('502') ||
        errorStr.contains('503') ||
        errorStr.contains('504') ||
        errorStr.contains('connection refused') ||
        errorStr.contains('not valid json'));
  }

  void _startHealthChecks() {
    _healthCheckTimer?.cancel();
    _healthCheckTimer = Timer.periodic(_checkInterval, (timer) {
      final elapsed = DateTime.now().difference(_deploymentStartTime!);
      if (elapsed > _maxWaitTime) {
        stopMonitoring();
      }
    });
  }

  void stopMonitoring() {
    _healthCheckTimer?.cancel();
    _healthCheckTimer = null;
    _isDeploying = false;
    _deploymentStartTime = null;
    _deploymentStateChanged.add(false);
  }

  void dispose() {
    _healthCheckTimer?.cancel();
    _deploymentStateChanged.close();
  }
}
