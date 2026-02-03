(function () {
  "use strict";

  function getCsrfToken() {
    var name = "csrftoken";
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var c = cookies[i].trim();
      if (c.indexOf(name + "=") === 0) {
        return c.substring(name.length + 1);
      }
    }
    return null;
  }

  function initWidget(container) {
    var hidden = container.querySelector('input[type="hidden"]');
    var searchInput = container.querySelector(".address-dadata-search");
    var dropdown = container.querySelector(".address-dadata-dropdown");
    var displayBlock = container.querySelector(".address-dadata-readonly");
    if (!hidden || !searchInput || !dropdown || !displayBlock) return;

    var suggestUrl = hidden.getAttribute("data-suggest-url");
    var createUrl = hidden.getAttribute("data-create-url");
    if (!suggestUrl || !createUrl) return;

    var debounceTimer = null;
    var currentSuggestions = [];

    function setAddressDisplay(data) {
      displayBlock.querySelector(".addr-city").textContent = data.city || "";
      displayBlock.querySelector(".addr-street").textContent = data.street || "";
      displayBlock.querySelector(".addr-house").textContent = data.house || "";
      displayBlock.querySelector(".addr-apartment").textContent = data.apartment || "";
      displayBlock.style.display = "block";
    }

    function hideDropdown() {
      dropdown.innerHTML = "";
      dropdown.setAttribute("aria-hidden", "true");
      currentSuggestions = [];
    }

    function showDropdown(items) {
      currentSuggestions = items;
      dropdown.innerHTML = "";
      items.forEach(function (item, index) {
        var div = document.createElement("div");
        div.className = "address-dadata-dropdown-item";
        div.setAttribute("role", "option");
        div.setAttribute("aria-selected", "false");
        div.setAttribute("data-index", String(index));
        div.textContent = item.value || "";
        dropdown.appendChild(div);
      });
      dropdown.setAttribute("aria-hidden", "false");
    }

    function fetchSuggestions(query, callback) {
      var url = suggestUrl + (suggestUrl.indexOf("?") >= 0 ? "&" : "?") + "query=" + encodeURIComponent(query);
      fetch(url, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (resp) {
          if (!resp.ok) throw new Error("HTTP " + resp.status);
          return resp.json();
        })
        .then(callback)
        .catch(function () {
          callback([]);
        });
    }

    function createAddressFromSuggestion(data, callback) {
      fetch(createUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify(data),
      })
        .then(function (resp) {
          if (!resp.ok) throw new Error("HTTP " + resp.status);
          return resp.json();
        })
        .then(callback)
        .catch(function () {
          callback(null);
        });
    }

    function onSearchInput() {
      var query = (searchInput.value || "").trim();
      if (query.length < 2) {
        hideDropdown();
        return;
      }
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        debounceTimer = null;
        fetchSuggestions(query, function (suggestions) {
          if (Array.isArray(suggestions) && suggestions.length > 0) {
            showDropdown(suggestions);
          } else {
            hideDropdown();
          }
        });
      }, 300);
    }

    function onSelectItem(index) {
      var item = currentSuggestions[Number(index)];
      if (!item || !item.data) {
        hideDropdown();
        return;
      }
      var data = item.data;
      createAddressFromSuggestion(
        {
          city: data.city || "",
          street: data.street || "",
          house: data.house || "",
          apartment: data.apartment || "",
          latitude: data.latitude != null ? data.latitude : null,
          longitude: data.longitude != null ? data.longitude : null,
        },
        function (result) {
          if (result && result.address_id) {
            hidden.value = result.address_id;
            if (hidden.dispatchEvent) {
              hidden.dispatchEvent(new Event("change", { bubbles: true }));
            }
            setAddressDisplay({
              city: data.city || "",
              street: data.street || "",
              house: data.house || "",
              apartment: data.apartment || "",
            });
            searchInput.value = item.value || "";
            hideDropdown();
          }
        }
      );
    }

    searchInput.addEventListener("input", onSearchInput);
    searchInput.addEventListener("focus", function () {
      var q = (searchInput.value || "").trim();
      if (q.length >= 2 && currentSuggestions.length === 0) {
        fetchSuggestions(q, function (suggestions) {
          if (Array.isArray(suggestions) && suggestions.length > 0) showDropdown(suggestions);
        });
      }
    });
    searchInput.addEventListener("blur", function () {
      setTimeout(hideDropdown, 200);
    });

    dropdown.addEventListener("click", function (e) {
      var item = e.target.closest(".address-dadata-dropdown-item");
      if (item) {
        var index = item.getAttribute("data-index");
        onSelectItem(index);
      }
    });

    dropdown.addEventListener("keydown", function (e) {
      var items = dropdown.querySelectorAll(".address-dadata-dropdown-item");
      if (items.length === 0) return;
      var current = dropdown.querySelector("[aria-selected=true]");
      var currentIndex = current ? parseInt(current.getAttribute("data-index"), 10) : -1;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        var next = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        items.forEach(function (el, i) {
          el.setAttribute("aria-selected", i === next ? "true" : "false");
        });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        var prev = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        items.forEach(function (el, i) {
          el.setAttribute("aria-selected", i === prev ? "true" : "false");
        });
      } else if (e.key === "Enter" && currentIndex >= 0) {
        e.preventDefault();
        onSelectItem(currentIndex);
      }
    });

    document.addEventListener("click", function (e) {
      if (!dropdown.contains(e.target) && e.target !== searchInput) {
        hideDropdown();
      }
    });
  }

  function init() {
    var widgets = document.querySelectorAll('input[data-suggest-url][data-create-url]');
    widgets.forEach(function (hidden) {
      var container = hidden.closest(".address-dadata-widget") || hidden.parentElement;
      if (container && !container.getAttribute("data-inited")) {
        container.setAttribute("data-inited", "1");
        initWidget(container);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
