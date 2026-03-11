import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_map/flutter_map.dart' as fmap;
import 'package:latlong2/latlong.dart' as latlong;
import 'package:ble_tracker_app/theme/app_theme.dart';
import 'package:ble_tracker_app/services/location_service.dart';
import 'package:ble_tracker_app/services/logger_service.dart';
import 'package:ble_tracker_app/models/trip_model.dart';

class TripDetailScreen extends StatefulWidget {
  final Trip trip;
  const TripDetailScreen({Key? key, required this.trip}) : super(key: key);

  @override
  State<TripDetailScreen> createState() => _TripDetailScreenState();
}

class _TripDetailScreenState extends State<TripDetailScreen> {
  final _locationService = LocationService();
  final _logger = LoggerService();

  List<TripEvent> _tripEvents = [];
  List<fmap.Polyline> _tripPolylines = [];
  List<fmap.Marker> _tripMarkers = [];
  bool _isLoading = true;
  fmap.LatLngBounds? _routeBounds;

  @override
  void initState() {
    super.initState();
    _loadTripRoute();
  }

  Future<void> _loadTripRoute() async {
    try {
      final events = await _locationService.getTripEvents(widget.trip.id);

      if (mounted) {
        setState(() {
          _tripEvents = events;
          _isLoading = false;
        });

        // Draw route on map
        _drawRoute(events);
      }
    } catch (e) {
      _logger.error('Failed to load trip route: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                Icon(Icons.error, color: Colors.white),
                SizedBox(width: 12),
                Expanded(child: Text('Failed to load route: $e')),
              ],
            ),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    }
  }

  void _drawRoute(List<TripEvent> events) {
    if (events.isEmpty) return;

    // Create polyline
    final points = events.map((e) => latlong.LatLng(e.latitude, e.longitude)).toList();

    final polyline = fmap.Polyline(
      points: points,
      color: AppTheme.brandPrimary,
      strokeWidth: 4.0,
      isDotted: false,
    );

    // Create start marker
    final startEvent = events.first;
    final startMarker = fmap.Marker(
      point: latlong.LatLng(startEvent.latitude, startEvent.longitude),
      width: 40,
      height: 40,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.green,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 4,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Icon(
          Icons.trip_origin,
          color: Colors.white,
          size: 24,
        ),
      ),
    );

    // Create end marker
    final endEvent = events.last;
    final endMarker = fmap.Marker(
      point: latlong.LatLng(endEvent.latitude, endEvent.longitude),
      width: 40,
      height: 40,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.red,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 4,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Icon(
          Icons.place,
          color: Colors.white,
          size: 24,
        ),
      ),
    );

    setState(() {
      _tripPolylines = [polyline];
      _tripMarkers = [startMarker, endMarker];
    });

    // Zoom map to show full route
    _zoomToRoute(points);
  }

  void _zoomToRoute(List<latlong.LatLng> points) {
    if (points.isEmpty) return;

    // Calculate bounds
    double minLat = points.first.latitude;
    double maxLat = points.first.latitude;
    double minLng = points.first.longitude;
    double maxLng = points.first.longitude;

    for (var point in points) {
      if (point.latitude < minLat) minLat = point.latitude;
      if (point.latitude > maxLat) maxLat = point.latitude;
      if (point.longitude < minLng) minLng = point.longitude;
      if (point.longitude > maxLng) maxLng = point.longitude;
    }

    // Add padding
    final latPadding = (maxLat - minLat) * 0.15;
    final lngPadding = (maxLng - minLng) * 0.15;

    final bounds = fmap.LatLngBounds(
      latlong.LatLng(minLat - latPadding, minLng - lngPadding),
      latlong.LatLng(maxLat + latPadding, maxLng + lngPadding),
    );

    setState(() {
      _routeBounds = bounds;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      body: SafeArea(
        child: Column(
          children: [
            // Header with back button
            Container(
              color: Colors.white,
              padding: EdgeInsets.all(16),
              child: Row(
                children: [
                  IconButton(
                    onPressed: Navigator.of(context).pop,
                    icon: Icon(Icons.arrow_back, color: AppTheme.brandPrimary),
                    tooltip: 'Back',
                  ),
                  Expanded(
                    child: Text(
                      'Trip Details',
                      style: GoogleFonts.poppins(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.brandPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Map view with boundary
            Expanded(
              flex: 1,
              child: Container(
                margin: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: AppTheme.brandPrimary.withOpacity(0.3),
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 12,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: _isLoading
                      ? Center(
                          child: CircularProgressIndicator(
                            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.brandPrimary),
                          ),
                        )
                      : fmap.FlutterMap(
                          options: fmap.MapOptions(
                            initialCenter: _routeBounds != null
                                ? latlong.LatLng(
                                    (_routeBounds!.south + _routeBounds!.north) / 2,
                                    (_routeBounds!.west + _routeBounds!.east) / 2,
                                  )
                                : (_tripEvents.isNotEmpty
                                    ? latlong.LatLng(_tripEvents.first.latitude, _tripEvents.first.longitude)
                                    : latlong.LatLng(0, 0)),
                            initialZoom: _routeBounds != null ? 12.0 : 13.0,
                          ),
                          children: [
                            fmap.TileLayer(
                              urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                              subdomains: ['a', 'b', 'c'],
                            ),
                            fmap.PolylineLayer(polylines: _tripPolylines),
                            fmap.MarkerLayer(markers: _tripMarkers),
                          ],
                        ),
                ),
              ),
            ),
            // Trip info box
            Container(
              color: Colors.white,
              child: SingleChildScrollView(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Trip date and time
                      Row(
                        children: [
                          Icon(Icons.calendar_today, size: 16, color: Colors.grey.shade600),
                          SizedBox(width: 8),
                          Text(
                            widget.trip.dateFormatted,
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade900,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 8),
                      // Start and end time
                      Row(
                        children: [
                          Icon(Icons.access_time, size: 16, color: Colors.grey.shade600),
                          SizedBox(width: 8),
                          Text(
                            '${widget.trip.startTimeFormatted} - ${widget.trip.endTimeFormatted}',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade900,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 12),
                      Divider(color: Colors.grey.shade300, height: 1),
                      SizedBox(height: 12),
                      // Vehicle
                      Row(
                        children: [
                          Container(
                            padding: EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppTheme.brandPrimary.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(Icons.directions_car, size: 18, color: AppTheme.brandPrimary),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Vehicle',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                                Text(
                                  widget.trip.vehicleDescription,
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.grey.shade900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 12),
                      // Distance
                      Row(
                        children: [
                          Container(
                            padding: EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(Icons.straighten, size: 18, color: Colors.blue.shade700),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Distance',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                                Text(
                                  widget.trip.formattedDistance,
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.blue.shade700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 12),
                      // Duration
                      Row(
                        children: [
                          Container(
                            padding: EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.orange.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(Icons.timer, size: 18, color: Colors.orange.shade700),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Duration',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                                Text(
                                  widget.trip.formattedDuration,
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.orange.shade700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 12),
                      // Start location
                      if (widget.trip.startLocationDescription != null) ...[
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(Icons.trip_origin, size: 18, color: Colors.green.shade700),
                            ),
                            SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Start Location',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: Colors.grey.shade600,
                                    ),
                                  ),
                                  Text(
                                    widget.trip.startLocationDescription!,
                                    style: GoogleFonts.inter(
                                      fontSize: 13,
                                      color: Colors.grey.shade900,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 12),
                      ],
                      // End location
                      if (widget.trip.endLocationDescription != null) ...[
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(Icons.place, size: 18, color: Colors.red.shade700),
                            ),
                            SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'End Location',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: Colors.grey.shade600,
                                    ),
                                  ),
                                  Text(
                                    widget.trip.endLocationDescription!,
                                    style: GoogleFonts.inter(
                                      fontSize: 13,
                                      color: Colors.grey.shade900,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 12),
                      ],
                      // Driver info
                      if (widget.trip.driverDescription != null) ...[
                        Row(
                          children: [
                            Container(
                              padding: EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.purple.shade50,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(Icons.person, size: 18, color: Colors.purple.shade700),
                            ),
                            SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Driver',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: Colors.grey.shade600,
                                    ),
                                  ),
                                  Text(
                                    widget.trip.driverDescription!,
                                    style: GoogleFonts.inter(
                                      fontSize: 13,
                                      color: Colors.grey.shade900,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    super.dispose();
  }
}
