(function () {
  "use strict";

  var DEFAULT_CENTER = [56.8389, 60.6057]; // Екатеринбург
  var DEFAULT_ZOOM = 11;

  function parseNum(s, def) {
    if (s == null || s === "") return def;
    var n = parseFloat(String(s).replace(",", "."));
    return isNaN(n) ? def : n;
  }

  function init() {
    var container = document.getElementById("store-map-container");
    if (!container) return;

    var mapEl = document.getElementById("store-map");
    if (!mapEl) return;

    var lat = parseNum(container.getAttribute("data-latitude"), null);
    var lng = parseNum(container.getAttribute("data-longitude"), null);
    var radiusKm = parseNum(container.getAttribute("data-delivery-radius-km"), 3);
    var addressId = container.getAttribute("data-address-id") || "";
    var coordinatesUrl = container.getAttribute("data-address-coordinates-url") || "";

    var hasCoords = lat != null && lng != null && !isNaN(lat) && !isNaN(lng);
    var center = hasCoords ? [lat, lng] : DEFAULT_CENTER;
    var radiusM = hasCoords && radiusKm > 0 ? radiusKm * 1000 : 0;

    var myMap = new ymaps.Map("store-map", {
      center: center,
      zoom: DEFAULT_ZOOM,
      controls: ["zoomControl", "typeSelector", "fullscreenControl"],
    });

    var placemark = new ymaps.Placemark(center, {}, { preset: "islands#redDotIcon" });
    var circle = null;

    if (hasCoords) {
      myMap.geoObjects.add(placemark);
      if (radiusM > 0) {
        circle = new ymaps.Circle(
          [center, radiusM],
          {},
          { fillColor: "0066ff99", strokeColor: "0066ff", strokeWidth: 2 }
        );
        myMap.geoObjects.add(circle);
      }
    }

    function fitMapToCircle() {
      if (!circle || !hasCoords) return;
      var bounds = circle.geometry.getBounds();
      if (bounds) myMap.setBounds(bounds, { checkZoomRange: true, zoomMargin: 50 });
    }

    if (hasCoords && radiusM > 0) fitMapToCircle();

    function updateFromCoords(newLat, newLng, newRadiusKm) {
      var r = parseNum(newRadiusKm, 3);
      var valid = newLat != null && newLng != null && !isNaN(newLat) && !isNaN(newLng);
      hasCoords = valid;
      if (valid) {
        center = [newLat, newLng];
        placemark.geometry.setCoordinates(center);
        myMap.geoObjects.add(placemark);
        var rm = r > 0 ? r * 1000 : 0;
        if (rm > 0) {
          if (!circle) {
            circle = new ymaps.Circle(
              [center, rm],
              {},
              { fillColor: "0066ff99", strokeColor: "0066ff", strokeWidth: 2 }
            );
            myMap.geoObjects.add(circle);
          } else {
            circle.geometry.setCoordinates(center);
            circle.geometry.setRadius(rm);
          }
          fitMapToCircle();
        } else {
          if (circle) {
            myMap.geoObjects.remove(circle);
            circle = null;
          }
          myMap.setCenter(center, myMap.getZoom(), { duration: 200 });
        }
      } else {
        myMap.geoObjects.remove(placemark);
        if (circle) {
          myMap.geoObjects.remove(circle);
          circle = null;
        }
        myMap.setCenter(DEFAULT_CENTER, DEFAULT_ZOOM, { duration: 200 });
      }
    }

    function updateRadiusOnly(newRadiusKm) {
      var r = parseNum(newRadiusKm, 3);
      var rm = r > 0 ? r * 1000 : 0;
      if (!hasCoords || !circle) {
        if (hasCoords && rm > 0) {
          circle = new ymaps.Circle(
            [center, rm],
            {},
            { fillColor: "0066ff99", strokeColor: "0066ff", strokeWidth: 2 }
          );
          myMap.geoObjects.add(circle);
          fitMapToCircle();
        }
        return;
      }
      if (rm > 0) {
        circle.geometry.setRadius(rm);
        fitMapToCircle();
      } else {
        myMap.geoObjects.remove(circle);
        circle = null;
        myMap.setCenter(center, myMap.getZoom(), { duration: 200 });
      }
    }

    var radiusInput = document.getElementById("id_delivery_radius_km");
    if (radiusInput) {
      function onRadiusChange() {
        updateRadiusOnly(radiusInput.value);
      }
      radiusInput.addEventListener("input", onRadiusChange);
      radiusInput.addEventListener("change", onRadiusChange);
    }

    var addressSelect = document.getElementById("id_address");
    if (addressSelect && coordinatesUrl) {
      addressSelect.addEventListener("change", function () {
        var id = (addressSelect.value || "").trim();
        if (!id) {
          updateFromCoords(null, null, radiusInput ? radiusInput.value : 3);
          return;
        }
        var url = coordinatesUrl.replace(/\/0\/?$/, "/" + id + "/");
        fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
          .then(function (resp) {
            if (!resp.ok) throw new Error("HTTP " + resp.status);
            return resp.json();
          })
          .then(function (data) {
            var la = data.latitude != null ? parseFloat(data.latitude) : null;
            var lo = data.longitude != null ? parseFloat(data.longitude) : null;
            updateFromCoords(la, lo, radiusInput ? radiusInput.value : 3);
          })
          .catch(function () {
            updateFromCoords(null, null, radiusInput ? radiusInput.value : 3);
          });
      });
    }
  }

  function run() {
    if (typeof ymaps === "undefined") return;
    ymaps.ready(init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
