window.document.addEventListener("DOMContentLoaded", function () {
    // Add collapse/expand buttons to code blocks that don't already have Quarto's code-fold buttons
    const codeBlocks = document.querySelectorAll('div.sourceCode:not(.code-fold-header-switched)');
    
    codeBlocks.forEach(function(codeBlock) {
      // Skip if this block already has controls
      if (codeBlock.querySelector('.code-block-buttons')) {
        return;
      }
      
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
        const preBlock = codeBlock.querySelector('pre');
        const isCollapsed = preBlock.classList.toggle('collapsed');
        toggleButton.innerHTML = isCollapsed ? '▶' : '▼';
        toggleButton.setAttribute('aria-label', 
          isCollapsed ? 'Expand code block' : 'Collapse code block'
        );
      });
      
      // Insert button before code block
      buttonContainer.appendChild(toggleButton);
      const preBlock = codeBlock.querySelector('pre');
      if (preBlock) {
        preBlock.parentNode.insertBefore(buttonContainer, preBlock);
      }
    });
  });