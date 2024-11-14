// Add $ to bash code blocks
$('div.language-bash code').each(function() {
  let code = $(this).text();
  if (code.endsWith('\n')) {
    code = code.slice(0, -1);
  }
  const lines = code.split('\n');
  const updatedLines = lines.map((line) => "$ " + line);
  $(this).text(updatedLines.join('\n'));
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

    // Check if the ancestor has the .language-bash class
    if (codeBlock.parentElement && codeBlock.parentElement.parentElement &&
        codeBlock.parentElement.parentElement.classList.contains('language-bash')) {
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
