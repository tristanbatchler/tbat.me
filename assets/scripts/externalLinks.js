for(var c = document.getElementsByTagName("a"), a = 0;a < c.length;a++) {
    var b = c[a];
    b.getAttribute("href") && b.hostname !== location.hostname && (b.target = "_blank")
    // Add icon to external links (not buttons or images)
    if (b.getAttribute("href") && b.hostname !== location.hostname && b.getElementsByTagName("img").length === 0 && b.getElementsByTagName("button").length === 0) {
        b.innerHTML += ' <i class="icon-external-link"></i>';
    }
}