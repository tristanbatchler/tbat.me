// Add $ to shell code blocks
document.querySelectorAll('div.language-shell code').forEach(function (codeBlock) {
  let contents = codeBlock.innerHTML;
  let lines = contents.split('\n');

  // Remove the last line if it's empty
  if (lines[lines.length - 1].trim() === '') {
    lines.pop();
  }
  
  // Add the $ to each line
  let updatedLines = lines.map(function (line) {
    return '<span class="sh-p">$ </span>' + line;
  });

  // Set the updated HTML back to the code block
  codeBlock.innerHTML = updatedLines.join('\n');
});

// Add copy button to all code blocks
document.querySelectorAll('pre.highlight').forEach(function (codeBlock) {
  // Create the copy button
  var button = document.createElement('button');
  button.className = 'copy-button';
  button.type = 'button';
  button.ariaLabel = 'Copy code to clipboard';
  button.innerText = 'Copy';

  // Prepend the button to the code block
  codeBlock.prepend(button);

  // Add event listener for copy functionality
  button.addEventListener('click', function () {
    var code = codeBlock.querySelector('code').innerText.trim();

    // Check if the ancestor has the .language-shell class
    if (codeBlock.parentElement &&
        codeBlock.parentElement.parentElement &&
        codeBlock.parentElement.parentElement.classList.contains('language-shell')) {
      // Remove the $ from the start of lines before copying
      code = code.replace(/^\$ /gm, '');
    }

    // Copy to clipboard
    window.navigator.clipboard.writeText(code).then(function() {
      button.innerText = 'Copied';
      setTimeout(function () {
        button.innerText = 'Copy';
      }, 4000);
    }).catch(function() {
      button.innerText = 'Failed';
    });
  });
});
