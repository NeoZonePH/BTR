/**
 * TARGET — Geolocation Module
 * Auto-detect browser geolocation for incident reporting.
 */

/**
 * Initialize geolocation detection.
 * @param {function} onSuccess - Callback with (lat, lng) on success
 * @param {function} onError - Callback on geolocation denial/error
 */
function initGeolocation(onSuccess, onError) {
    if (!navigator.geolocation) {
        console.warn('Geolocation not supported by this browser.');
        if (onError) onError('Geolocation not supported');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function (position) {
            const lat = position.coords.latitude.toFixed(7);
            const lng = position.coords.longitude.toFixed(7);
            if (onSuccess) onSuccess(lat, lng);
        },
        function (error) {
            console.warn('Geolocation error:', error.message);
            if (onError) onError(error.message);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
        }
    );
}
