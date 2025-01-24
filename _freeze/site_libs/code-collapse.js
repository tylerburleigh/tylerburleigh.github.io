window.document.addEventListener("DOMContentLoaded", function () {
    // Add collapse/expand buttons to all code blocks
    const codeBlocks = document.querySelectorAll('pre.sourceCode');
    
    codeBlocks.forEach(function(codeBlock) {
      // Create button container
      const buttonContainer = document.createElement('div');
      buttonContainer.className = 'code-block-buttons';
      
      // Create collapse/expand button
      const toggleButton = document.createElement('button');
      toggleButton.className = 'code-collapse-btn';
      toggleButton.innerHTML = '▼';
      toggleButton.setAttribute('aria-label', 'Collapse code block');
      
      // Add click handler
      toggleButton.addEventListener('click', function() {
        const isCollapsed = codeBlock.classList.toggle('collapsed');
        toggleButton.innerHTML = isCollapsed ? '▶' : '▼';
        toggleButton.setAttribute('aria-label', 
          isCollapsed ? 'Expand code block' : 'Collapse code block'
        );
      });
      
      // Insert button before code block
      buttonContainer.appendChild(toggleButton);
      codeBlock.parentNode.insertBefore(buttonContainer, codeBlock);
    });
  });