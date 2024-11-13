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


// Add copy button to code blocks
var codeBlocks = document.querySelectorAll('pre.highlight');
codeBlocks.forEach(function (codeBlock) {
  var  Button = document.createElement('button');
   Button.className = 'copy-button';
   Button.type = 'button';
   Button.ariaLabel = 'Copy code to clipboard';
   Button.innerText = 'Copy'


  codeBlock.prepend( Button);


   Button.addEventListener('click', function () {
    var code = codeBlock.querySelector('code').innerText.trim();

    // Strip leading $ from .language-bash blocks
    if (codeBlock.classList.contains('language-bash')) {
      code = code.replace(/^\$ /gm, '');
    }

    window.navigator.clipboard.writeText(code);


     Button.innerText = 'Copied';
    var fourSeconds = 4000;


    setTimeout(function () {
       Button.innerText = 'Copy'
    }, fourSeconds);
  });
});
