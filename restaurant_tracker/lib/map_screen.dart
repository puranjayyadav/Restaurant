import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';

class MapScreen extends StatefulWidget {
  final Function(LatLng)
      onLocationUpdated; // Callback to pass location to caller

  const MapScreen({super.key, required this.onLocationUpdated});

  @override
  _MapScreenState createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  GoogleMapController? _mapController;
  LatLng _currentPosition = LatLng(0, 0);

  @override
  void initState() {
    super.initState();
    _determinePosition();
  }

  Future<void> _determinePosition() async {
    // Request permissions if needed.
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Location services are disabled.')),
      );
      return;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      permission = await Geolocator.requestPermission();
      if (permission != LocationPermission.always &&
          permission != LocationPermission.whileInUse) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Location permissions are denied.')),
        );
        return;
      }
    }

    try {
      // Get current position with high accuracy.
      Position position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high);

      setState(() {
        _currentPosition = LatLng(position.latitude, position.longitude);
      });

      // Inform the parent widget about the current location.
      widget.onLocationUpdated(_currentPosition);

      // Move the camera to the current position if the map is ready.
      _mapController?.animateCamera(CameraUpdate.newLatLng(_currentPosition));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error retrieving location: $e')),
      );
    }
  }

  void _onConfirmLocation() {
    // Optionally, call the callback again if you want to update before popping.
    widget.onLocationUpdated(_currentPosition);
    // Return the chosen location to the previous screen.
    Navigator.pop(context, _currentPosition);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Select Your Location'),
      ),
      body: GoogleMap(
        onMapCreated: (controller) {
          _mapController = controller;
          // If a valid location exists, move the camera there.
          if (_currentPosition.latitude != 0 &&
              _currentPosition.longitude != 0) {
            _mapController!
                .animateCamera(CameraUpdate.newLatLng(_currentPosition));
          }
        },
        initialCameraPosition: CameraPosition(
          target: _currentPosition,
          zoom: 14,
        ),
        myLocationEnabled: true,
        myLocationButtonEnabled: true,
        onCameraMove: (CameraPosition position) {
          // Update current position as the map moves.
          _currentPosition = position.target;
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _onConfirmLocation,
        tooltip: 'Confirm Location',
        child: const Icon(Icons.check),
      ),
    );
  }
}
