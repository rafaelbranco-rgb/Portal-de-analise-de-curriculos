/* Efeito 3D tilt para .glass-tile-3d
   Atualiza --mx e --my com base na posição do cursor.
   Inspirado em plano-intermitentes/glass-tile-3d. */
(function () {
  "use strict";

  function handleMove(e) {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const mx = ((e.clientX - r.left) / r.width) * 100;
    const my = ((e.clientY - r.top) / r.height) * 100;
    el.style.setProperty("--mx", String(mx));
    el.style.setProperty("--my", String(my));
  }

  function handleLeave(e) {
    const el = e.currentTarget;
    el.style.setProperty("--mx", "50");
    el.style.setProperty("--my", "50");
  }

  function bind(root) {
    const tiles = (root || document).querySelectorAll(".glass-tile-3d");
    tiles.forEach(function (t) {
      if (t.dataset.tiltBound === "1") return;
      t.dataset.tiltBound = "1";
      t.addEventListener("mousemove", handleMove);
      t.addEventListener("mouseleave", handleLeave);
    });
  }

  window.LiquidTilt = { bind: bind };

  document.addEventListener("DOMContentLoaded", function () {
    bind(document);
  });
})();
