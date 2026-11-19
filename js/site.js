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
}());
