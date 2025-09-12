// simple UI helpers (no frameworks)
document.addEventListener('DOMContentLoaded', () => {
  // optional: smooth appearance for cards
  document.querySelectorAll('.card').forEach((el, idx)=>{
    el.style.opacity = 0;
    setTimeout(()=>{ el.style.transition='all 500ms'; el.style.opacity=1; el.style.transform='translateY(0)'; }, 80*idx);
  });
});
