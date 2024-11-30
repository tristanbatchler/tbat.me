// Add $ to shell code blocks
$('div.language-shell code').each(function() {
  let contents = $(this).html();
  let lines = contents.split('\n');

  // Remove the last line if it's empty
  if (lines[lines.length - 1].trim() === '') {
    lines.pop();
  }
  
  let updatedLines = lines.map(function(line) {
    return '<span class="sh-p">$ </span>' + line;
  });

  $(this).html(updatedLines.join('\n'));

});

// Add copy button to all code blocks
var codeBlocks = document.querySelectorAll('pre.highlight');
codeBlocks.forEach(function (codeBlock) {
  var button = document.createElement('button');
  button.className = 'copy-button';
  button.type = 'button';
  button.ariaLabel = 'Copy code to clipboard';
  button.innerText = 'Copy';

  codeBlock.prepend(button);

  button.addEventListener('click', function () {
    var code = codeBlock.querySelector('code').innerText.trim();

    // Check if the ancestor has the .language-shell class
    if (codeBlock.parentElement && codeBlock.parentElement.parentElement &&
        codeBlock.parentElement.parentElement.classList.contains('language-shell')) {
      code = code.replace(/^\$ /gm, '');
    }

    window.navigator.clipboard.writeText(code);

    button.innerText = 'Copied';
    var fourSeconds = 4000;

    setTimeout(function () {
      button.innerText = 'Copy';
    }, fourSeconds);
  });
});
