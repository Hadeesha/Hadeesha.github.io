(function () {
  "use strict";

  var cfg = window.SITE_CONFIG;
  if (!cfg) {
    return;
  }

  function lookup(path) {
    var node = cfg;
    var parts = path.split(".");
    var i;
    for (i = 0; i < parts.length; i += 1) {
      if (node == null) {
        return undefined;
      }
      node = node[parts[i]];
    }
    return node;
  }

  var nodes = document.querySelectorAll("[data-config]");
  var n;
  for (n = 0; n < nodes.length; n += 1) {
    var el = nodes[n];
    var key = el.getAttribute("data-config");
    var value = lookup(key);
    if (value == null || value === "") {
      continue;
    }
    var text = String(value);
    var realEmail = key === "contact.email" &&
      text.indexOf("@") !== -1 &&
      text.indexOf("[") === -1 &&
      text.indexOf(" ") === -1;
    if (realEmail) {
      var link = document.createElement("a");
      link.href = "mailto:" + text;
      link.textContent = text;
      el.textContent = "";
      el.appendChild(link);
    } else {
      el.textContent = text;
    }
  }

  var pageTitle = document.body.getAttribute("data-page-title");
  if (cfg.labName && document.title.indexOf(" | ") === -1) {
    document.title = pageTitle ? pageTitle + " · " + cfg.labName : cfg.labName;
  }

  var dialog = document.querySelector(".figure-lightbox");
  if (dialog && typeof dialog.showModal === "function") {
    var closeBtn = dialog.querySelector(".figure-lightbox-close");
    var view = document.createElement("img");
    var opener = null;
    view.className = "figure-lightbox-image";
    dialog.appendChild(view);

    function openFigure(button) {
      var source = button.querySelector("img");
      var full = button.getAttribute("data-full");
      if (!source || !full) {
        return;
      }
      view.src = full;
      view.alt = source.getAttribute("alt") || "";
      opener = button;
      dialog.showModal();
      closeBtn.focus();
    }

    function shutFigure() {
      if (dialog.open) {
        dialog.close();
      }
    }

    var zoomButtons = document.querySelectorAll(".figure-zoom");
    var z;
    for (z = 0; z < zoomButtons.length; z += 1) {
      zoomButtons[z].addEventListener("click", function () {
        openFigure(this);
      });
    }
    closeBtn.addEventListener("click", shutFigure);
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        shutFigure();
      }
    });
    dialog.addEventListener("close", function () {
      view.removeAttribute("src");
      if (opener) {
        opener.focus();
        opener = null;
      }
    });
  }
}());
