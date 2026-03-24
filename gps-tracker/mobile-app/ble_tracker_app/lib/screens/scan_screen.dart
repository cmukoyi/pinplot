import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart' as fmap;
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart' as latlong;

import 'package:ble_tracker_app/models/beacon_sighting_model.dart';
import 'package:ble_tracker_app/services/ble_scan_service.dart';
import 'package:ble_tracker_app/services/pareto_decoder.dart';
import 'package:ble_tracker_app/theme/app_theme.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({Key? key}) : super(key: key);

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final BLEScanService _service = BLEScanService();
  final fmap.MapController _mapController = fmap.MapController();

  List<DiscoveredBeacon> _discovered = [];
  List<BeaconLocation> _savedLocations = [];
  bool _isScanning = false;
  bool _loadingLocations = false;
  String? _error;

  StreamSubscription<List<DiscoveredBeacon>>? _beaconSub;
  StreamSubscription<bool>? _scanningSub;

  // Default map centre (London UK). Overridden when beacons are available.
  latlong.LatLng _mapCentre = const latlong.LatLng(51.5074, -0.1278);
  double _mapZoom = 5.0;

  @override
  void initState() {
    super.initState();
    _beaconSub = _service.beaconStream.listen((beacons) {
      if (mounted) setState(() => _discovered = beacons);
    });
    _scanningSub = _service.scanningStream.listen((scanning) {
      if (mounted) setState(() => _isScanning = scanning);
    });
    _loadSavedLocations();
  }

  @override
  void dispose() {
    _beaconSub?.cancel();
    _scanningSub?.cancel();
    // Don't stop the scan on dispose – user may have navigated to another tab;
    // stopping is explicit via the Stop button.
    super.dispose();
  }

  Future<void> _loadSavedLocations() async {
    setState(() => _loadingLocations = true);
    final locs = await _service.getBeaconLocations();
    if (!mounted) return;
    setState(() {
      _savedLocations = locs;
      _loadingLocations = false;
      if (locs.isNotEmpty) {
        _mapCentre = latlong.LatLng(locs.first.lat, locs.first.lon);
        _mapZoom = 13.0;
      }
    });
  }

  Future<void> _toggleScan() async {
    setState(() => _error = null);
    try {
      if (_isScanning) {
        await _service.stopScan();
        // Refresh saved locations after a scan ends.
        await _loadSavedLocations();
      } else {
        await _service.startScan(timeout: const Duration(seconds: 30));
      }
    } on UnsupportedError catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(
          () => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) return _buildWebUnavailable();

    return Column(
      children: [
        // Space below the top nav bar rendered by MapScreen's Stack.
        const SizedBox(height: 80),

        // ── Map area ──────────────────────────────────────────────────────
        Expanded(child: _buildMap()),

        // ── Control panel ─────────────────────────────────────────────────
        _buildControlPanel(),
      ],
    );
  }

  Widget _buildMap() {
    final markers = _buildMarkers();
    return fmap.FlutterMap(
      mapController: _mapController,
      options: fmap.MapOptions(
        initialCenter: _mapCentre,
        initialZoom: _mapZoom,
        interactionOptions: const fmap.InteractionOptions(
          flags: fmap.InteractiveFlag.all,
        ),
      ),
      children: [
        fmap.TileLayer(
          urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          subdomains: const ['a', 'b', 'c'],
          userAgentPackageName: 'com.beacontelematics.tracker',
          maxZoom: 18,
          tileSize: 256,
          tileDisplay: fmap.TileDisplay.fadeIn(
            duration: const Duration(milliseconds: 50),
          ),
        ),
        if (markers.isNotEmpty) fmap.MarkerLayer(markers: markers),
      ],
    );
  }

  List<fmap.Marker> _buildMarkers() {
    final markers = <fmap.Marker>[];

    // Build a set of IDs that were detected as Pareto devices in this session.
    final paretoIds = {
      for (final b in _discovered)
        if (ParetoDecoder.decode(b).isPareto) b.id,
    };

    for (final loc in _savedLocations) {
      final isPareto = paretoIds.contains(loc.tagId);
      final color = isPareto ? Colors.indigo.shade700 : Colors.teal.shade700;
      final icon = isPareto ? Icons.sensors : Icons.bluetooth;
      final paretoType = isPareto
          ? ParetoDecoder.decode(
              _discovered.firstWhere((b) => b.id == loc.tagId))
          : null;

      markers.add(
        fmap.Marker(
          point: latlong.LatLng(loc.lat, loc.lon),
          width: 44,
          height: 44,
          child: Tooltip(
            message: '${loc.displayName}'
                '${paretoType != null ? ' · ${paretoType.typeLabel}' : ''}\n'
                'Last seen: ${_formatTime(loc.lastSeen)}',
            child: Container(
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: const [
                  BoxShadow(color: Colors.black26, blurRadius: 4)
                ],
              ),
              child: Icon(icon, color: Colors.white, size: 20),
            ),
          ),
        ),
      );
    }

    return markers;
  }

  Widget _buildControlPanel() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.12),
            blurRadius: 12,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // ── Scan button row ──
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                Expanded(child: _buildScanButton()),
                const SizedBox(width: 12),
                _buildRefreshButton(),
              ],
            ),
          ),

          // ── Error banner ──
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(
                  _error!,
                  style: GoogleFonts.inter(color: Colors.red.shade700, fontSize: 13),
                ),
              ),
            ),

          // ── Nearby beacons list ──
          _buildNearbyList(),

          // ── Pareto summary bar ──
          _buildParetoSummary(),

          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _buildParetoSummary() {
    final paretoCount =
        _discovered.where((b) => ParetoDecoder.decode(b).isPareto).length;
    if (paretoCount == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
      child: Row(
        children: [
          Icon(Icons.sensors, size: 14, color: Colors.indigo.shade600),
          const SizedBox(width: 6),
          Text(
            '$paretoCount Pareto-compatible device${paretoCount != 1 ? 's' : ''} nearby',
            style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.indigo.shade700,
                fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildScanButton() {
    return SizedBox(
      height: 48,
      child: ElevatedButton.icon(
        onPressed: _toggleScan,
        icon: Icon(
          _isScanning ? Icons.stop_circle_outlined : Icons.bluetooth_searching,
          size: 22,
        ),
        label: Text(
          _isScanning ? 'Stop Scan' : 'Start Scan',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 15),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: _isScanning ? Colors.red.shade600 : AppTheme.brandPrimary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }

  Widget _buildRefreshButton() {
    return SizedBox(
      height: 48,
      width: 48,
      child: IconButton.filled(
        onPressed: _loadingLocations ? null : _loadSavedLocations,
        icon: _loadingLocations
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.refresh, size: 22),
        style: IconButton.styleFrom(
          backgroundColor: AppTheme.brandPrimaryHover,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }

  Widget _buildNearbyList() {
    if (!_isScanning && _discovered.isEmpty) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 16, color: Colors.grey.shade500),
            const SizedBox(width: 6),
            Text(
              _savedLocations.isEmpty
                  ? 'Tap Start Scan to find nearby BLE tags'
                  : '${_savedLocations.length} tag${_savedLocations.length != 1 ? 's' : ''} on map  •  tap Start Scan to update',
              style: GoogleFonts.inter(color: Colors.grey.shade600, fontSize: 13),
            ),
          ],
        ),
      );
    }

    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 180),
      child: ListView.builder(
        shrinkWrap: true,
        padding: const EdgeInsets.only(bottom: 4),
        itemCount: _discovered.isEmpty ? 0 : _discovered.length,
        itemBuilder: (context, index) {
          final beacon = _discovered[index];
          return _BeaconListTile(beacon: beacon);
        },
      ),
    );
  }

  Widget _buildWebUnavailable() {
    return Padding(
      padding: const EdgeInsets.only(top: 80),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.bluetooth_disabled,
                  size: 64, color: Colors.grey.shade400),
              const SizedBox(height: 20),
              Text(
                'BLE Scanning requires the mobile app',
                style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey.shade700),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                'Download the Pinplot app on Android or iOS to scan for nearby BLE tags and report their locations.',
                style: GoogleFonts.inter(
                    fontSize: 14, color: Colors.grey.shade500),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inHours < 1) return '${diff.inMinutes}m ago';
    if (diff.inDays < 1) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

// ── Beacon list tile ─────────────────────────────────────────────────────────

class _BeaconListTile extends StatelessWidget {
  const _BeaconListTile({required this.beacon});
  final DiscoveredBeacon beacon;

  @override
  Widget build(BuildContext context) {
    final paretoInfo = ParetoDecoder.decode(beacon);
    final isPareto = paretoInfo.isPareto;

    final iconBg = isPareto ? Colors.indigo.shade50 : AppTheme.brandPrimaryLight;
    final iconColor = isPareto ? Colors.indigo.shade700 : AppTheme.brandPrimary;
    final iconData = isPareto ? Icons.sensors : Icons.bluetooth;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isPareto ? Colors.indigo.shade50.withOpacity(0.4) : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isPareto ? Colors.indigo.shade100 : Colors.grey.shade200,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: iconBg,
              shape: BoxShape.circle,
            ),
            child: Icon(iconData, color: iconColor, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  beacon.displayName,
                  style: GoogleFonts.inter(
                      fontWeight: FontWeight.w600, fontSize: 13),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  beacon.id,
                  style: GoogleFonts.inter(
                      fontSize: 11, color: Colors.grey.shade600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (isPareto) ...
                  [
                    const SizedBox(height: 3),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade100,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        paretoInfo.typeLabel,
                        style: GoogleFonts.inter(
                            fontSize: 10,
                            color: Colors.indigo.shade800,
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
              ],
            ),
          ),
          _SignalBars(bars: beacon.signalBars, rssi: beacon.rssi),
        ],
      ),
    );
  }
}

// ── Signal bars widget ───────────────────────────────────────────────────────

class _SignalBars extends StatelessWidget {
  const _SignalBars({required this.bars, required this.rssi});
  final int bars;
  final int rssi;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: List.generate(4, (i) {
            final active = i < bars;
            return Container(
              width: 4,
              height: 6.0 + i * 4,
              margin: const EdgeInsets.symmetric(horizontal: 1),
              decoration: BoxDecoration(
                color: active ? AppTheme.brandPrimary : Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
        ),
        const SizedBox(height: 2),
        Text(
          '${rssi} dBm',
          style:
              GoogleFonts.inter(fontSize: 10, color: Colors.grey.shade600),
        ),
      ],
    );
  }
}
