for(var c = document.getElementsByTagName("a"), a = 0;a < c.length;a++) {
    var b = c[a];
    if (b.getAttribute("href") && b.hostname !== location.hostname) {
        b.target = "_blank";

        var relValues = (b.getAttribute("rel") || "").split(/\s+/).filter(Boolean);
        if (relValues.indexOf("noopener") === -1) relValues.push("noopener");
        if (relValues.indexOf("noreferrer") === -1) relValues.push("noreferrer");
        b.setAttribute("rel", relValues.join(" "));
    }
    // Add icon to external links (not buttons or images or icons)
    if (b.getAttribute("href") && b.hostname !== location.hostname && b.getElementsByTagName("img").length === 0 && b.getElementsByTagName("button").length === 0 && b.getElementsByTagName("i").length === 0) {
        b.innerHTML += ' <i class="icon-external-link"></i>';
    }
}