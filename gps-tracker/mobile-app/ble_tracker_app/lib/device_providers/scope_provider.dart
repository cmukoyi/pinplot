/// Scope / MZone BLE tag provider.
///
/// Delegates validation to the Pinplot backend. The live MZone match
/// happens at the next polling cycle once the tag is registered.
import '../device_providers/ble_tag_type.dart';
import '../device_providers/ble_tag_provider.dart';
import '../services/auth_service.dart';

class ScopeTagProvider implements BleTagProvider {
  final AuthService _authService;

  ScopeTagProvider(this._authService);

  @override
  BleTagType get tagType => BleTagType.scope;

  @override
  String get displayName => 'Scope';

  @override
  Future<TagValidationResult> validateTag(String imei) async {
    final result =
        await _authService.validateTagByType(imei, BleTagType.scope.apiValue);
    return TagValidationResult(
      isValid: result['is_valid'] as bool,
      message: result['message'] as String,
    );
  }
}
