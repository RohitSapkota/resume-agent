// script.js
// Minimal, purposeful JS: print button and certification expand toggle if necessary.
document.addEventListener('DOMContentLoaded', function(){
  var printBtn = document.getElementById('printBtn');
  if(printBtn){
    printBtn.addEventListener('click', function(){
      window.print();
    });
  }

  // Improve keyboard focus order: ensure skip link focuses main when used
  var skip = document.querySelector('.skip-link');
  if(skip){
    skip.addEventListener('click', function(e){
      var main = document.getElementById('main');
      if(main){
        main.setAttribute('tabindex','-1');
        main.focus();
      }
    });
  }
});
