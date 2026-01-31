// Initialize Mermaid diagrams
// This script is loaded after the page content

document$.subscribe(function() {
  mermaid.initialize({
    startOnLoad: true,
    theme: document.body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "default",
    securityLevel: "loose",
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: "basis"
    }
  });
  
  // Re-render mermaid diagrams
  mermaid.contentLoaded();
  
  // Apply animations after a short delay to ensure SVG is rendered
  setTimeout(applyFlowAnimations, 500);
});

// Apply flowing animation to arrow paths
function applyFlowAnimations() {
  document.querySelectorAll('.mermaid svg').forEach(function(svg) {
    // Find all edge/link paths
    const paths = svg.querySelectorAll('.edgePath path, path.flowchart-link, .edge path');
    paths.forEach(function(path) {
      // Apply animation styles directly
      path.style.strokeDasharray = '10 5';
      path.style.animation = 'flowArrow 0.8s linear infinite';
    });
  });
}

// Handle theme changes
const observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "data-md-color-scheme") {
      const theme = document.body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "default";
      mermaid.initialize({ theme: theme });
      document.querySelectorAll(".mermaid").forEach(function(el) {
        // Force re-render by removing processed state
        el.removeAttribute("data-processed");
      });
      mermaid.contentLoaded();
      setTimeout(applyFlowAnimations, 500);
    }
  });
});

observer.observe(document.body, { attributes: true });
