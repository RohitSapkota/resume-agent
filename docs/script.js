// script.js — minimal, purposeful behavior
document.addEventListener('DOMContentLoaded', function(){
  var printBtn = document.getElementById('printBtn');
  if(printBtn){
    printBtn.addEventListener('click', function(){
      window.print();
    });
  }

  // Improve skip link behaviour for older browsers
  var skip = document.querySelector('.skip-link');
  if(skip){
    skip.addEventListener('click', function(e){
      var main = document.getElementById('main');
      if(main){
        main.setAttribute('tabindex','-1');
        main.focus({preventScroll:false});
        main.removeAttribute('tabindex');
      }
    });
  }
});
