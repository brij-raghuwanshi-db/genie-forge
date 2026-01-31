/**
 * Genie-Forge Documentation - Interactive Features
 * 
 * This script provides:
 * - Enhanced Mermaid diagram interactivity
 * - Terminal demo simulation
 * - Diagram zoom controls
 * - Copy-to-clipboard enhancements
 */

// Wait for document to be ready
document.addEventListener('DOMContentLoaded', function() {
  initMermaidEnhancements();
  initTerminalDemo();
  initDiagramControls();
});

// Also handle instant loading (Material for MkDocs)
if (typeof document$ !== 'undefined') {
  document$.subscribe(function() {
    initMermaidEnhancements();
    initTerminalDemo();
    initDiagramControls();
  });
}

/**
 * Enhanced Mermaid Diagram Features
 */
function initMermaidEnhancements() {
  // Add click handlers to mermaid nodes for highlighting
  const mermaidDiagrams = document.querySelectorAll('.mermaid');
  
  mermaidDiagrams.forEach(function(diagram) {
    // Add interactive class
    diagram.classList.add('interactive');
    
    // Find all nodes and add click handlers
    const nodes = diagram.querySelectorAll('.node');
    nodes.forEach(function(node) {
      node.addEventListener('click', function(e) {
        // Remove highlight from all nodes
        nodes.forEach(function(n) { n.classList.remove('highlighted'); });
        // Add highlight to clicked node
        this.classList.add('highlighted');
        e.stopPropagation();
      });
    });
    
    // Click outside to remove highlights
    diagram.addEventListener('click', function(e) {
      if (e.target === this || e.target.tagName === 'svg') {
        nodes.forEach(function(n) { n.classList.remove('highlighted'); });
      }
    });
  });
  
  // Add animation control buttons to live diagrams
  const liveDiagrams = document.querySelectorAll('.live-diagram');
  liveDiagrams.forEach(function(container) {
    if (!container.querySelector('.diagram-controls')) {
      addDiagramControls(container);
    }
  });
}

/**
 * Add control buttons to diagram containers
 */
function addDiagramControls(container) {
  const controls = document.createElement('div');
  controls.className = 'diagram-controls';
  controls.innerHTML = `
    <button class="diagram-btn" data-action="pause" title="Pause/Play Animation">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
      </svg>
    </button>
    <button class="diagram-btn" data-action="reset" title="Reset View">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
      </svg>
    </button>
  `;
  
  // Style the controls
  controls.style.cssText = `
    position: absolute;
    top: 0.5rem;
    left: 0.5rem;
    display: flex;
    gap: 0.25rem;
    z-index: 10;
  `;
  
  container.style.position = 'relative';
  container.insertBefore(controls, container.firstChild);
  
  // Add event listeners
  const pauseBtn = controls.querySelector('[data-action="pause"]');
  const resetBtn = controls.querySelector('[data-action="reset"]');
  
  let isPaused = false;
  
  pauseBtn.addEventListener('click', function() {
    isPaused = !isPaused;
    const mermaid = container.querySelector('.mermaid');
    if (mermaid) {
      if (isPaused) {
        mermaid.style.setProperty('--animation-state', 'paused');
        mermaid.querySelectorAll('.flowchart-link, .edgePath path').forEach(function(el) {
          el.style.animationPlayState = 'paused';
        });
        this.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
      } else {
        mermaid.style.removeProperty('--animation-state');
        mermaid.querySelectorAll('.flowchart-link, .edgePath path').forEach(function(el) {
          el.style.animationPlayState = 'running';
        });
        this.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>`;
      }
    }
  });
  
  resetBtn.addEventListener('click', function() {
    // Reset any panzoom transformations
    const mermaid = container.querySelector('.mermaid');
    if (mermaid) {
      mermaid.style.transform = '';
    }
  });
}

/**
 * Interactive Terminal Demo
 */
function initTerminalDemo() {
  const terminals = document.querySelectorAll('.terminal-demo');
  
  terminals.forEach(function(terminal) {
    const commands = JSON.parse(terminal.dataset.commands || '{}');
    const outputEl = terminal.querySelector('.terminal-output');
    const inputEl = terminal.querySelector('.terminal-input');
    
    if (!inputEl || !outputEl) return;
    
    // Command history
    let history = [];
    let historyIndex = -1;
    
    inputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        const cmd = this.value.trim();
        if (cmd) {
          history.push(cmd);
          historyIndex = history.length;
          executeCommand(cmd, commands, outputEl);
          this.value = '';
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIndex > 0) {
          historyIndex--;
          this.value = history[historyIndex];
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex < history.length - 1) {
          historyIndex++;
          this.value = history[historyIndex];
        } else {
          historyIndex = history.length;
          this.value = '';
        }
      }
    });
  });
}

/**
 * Execute a command in the terminal demo
 */
function executeCommand(cmd, commands, outputEl) {
  const prompt = '<span class="terminal-prompt">$ </span>';
  const commandLine = `${prompt}<span class="terminal-command">${escapeHtml(cmd)}</span>\n`;
  
  let output = '';
  
  // Check for exact match first
  if (commands[cmd]) {
    output = commands[cmd];
  } 
  // Check for partial matches (e.g., "genie-forge --help" matches "genie-forge")
  else {
    const baseCmd = cmd.split(' ')[0];
    if (commands[baseCmd]) {
      output = commands[baseCmd];
    } else if (cmd.includes('help') || cmd === '--help' || cmd === '-h') {
      output = getHelpText();
    } else {
      output = `<span style="color: #f44336;">Command not found: ${escapeHtml(cmd)}</span>\nType 'help' for available commands.`;
    }
  }
  
  outputEl.innerHTML += commandLine + `<span class="terminal-output">${output}</span>\n\n`;
  outputEl.scrollTop = outputEl.scrollHeight;
}

/**
 * Get help text for terminal demo
 */
function getHelpText() {
  return `<span style="color: #4ec9b0;">Available demo commands:</span>

  genie-forge --help      Show CLI help
  genie-forge whoami      Display current workspace
  genie-forge space-list  List all Genie spaces
  genie-forge plan        Preview deployment changes
  genie-forge apply       Apply configuration
  genie-forge status      Show deployment status
  
<span style="color: #888;">This is an interactive demo. Try the commands above!</span>`;
}

/**
 * Initialize diagram zoom controls
 */
function initDiagramControls() {
  // Add zoom hint to diagrams that support panzoom
  const diagrams = document.querySelectorAll('.mermaid');
  
  diagrams.forEach(function(diagram) {
    // Check if panzoom is enabled (from mkdocs-panzoom plugin)
    if (diagram.closest('.panzoom-enabled') || diagram.classList.contains('panzoom')) {
      const hint = document.createElement('div');
      hint.className = 'zoom-hint';
      hint.innerHTML = '<kbd>Alt</kbd> + Scroll to zoom • Drag to pan';
      hint.style.cssText = `
        position: absolute;
        bottom: 0.5rem;
        right: 0.5rem;
        font-size: 0.7rem;
        color: var(--md-default-fg-color--light);
        opacity: 0;
        transition: opacity 0.3s;
        pointer-events: none;
        background: var(--md-default-bg-color);
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
      `;
      
      const parent = diagram.parentElement;
      if (parent) {
        parent.style.position = 'relative';
        parent.appendChild(hint);
        
        parent.addEventListener('mouseenter', function() {
          hint.style.opacity = '0.8';
        });
        parent.addEventListener('mouseleave', function() {
          hint.style.opacity = '0';
        });
      }
    }
  });
}

/**
 * Utility: Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Utility: Add styles for diagram controls
 */
(function addDiagramStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .diagram-btn {
      background: var(--md-default-bg-color);
      border: 1px solid var(--md-default-fg-color--lightest);
      border-radius: 0.25rem;
      padding: 0.25rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--md-default-fg-color--light);
      transition: all 0.2s;
    }
    
    .diagram-btn:hover {
      background: var(--md-accent-fg-color);
      color: var(--md-accent-bg-color);
      border-color: var(--md-accent-fg-color);
    }
    
    .mermaid .node.highlighted rect,
    .mermaid .node.highlighted circle,
    .mermaid .node.highlighted polygon {
      stroke: var(--md-accent-fg-color) !important;
      stroke-width: 3px !important;
      filter: drop-shadow(0 0 8px var(--md-accent-fg-color));
    }
  `;
  document.head.appendChild(style);
})();
