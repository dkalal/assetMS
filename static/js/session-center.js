(function(){
  'use strict';
  const root=document.querySelector('[data-session-center]');if(!root)return;
  const alertBox=root.querySelector('[data-session-alert]');const csrf=root.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
  root.querySelector('[data-refresh-sessions]')?.addEventListener('click',()=>window.location.reload());
  root.querySelector('[data-cleanup-sessions]')?.addEventListener('click',async event=>{if(!window.confirm('Mark tracked sessions inactive when they have had no activity for 24 hours?'))return;const button=event.currentTarget;button.disabled=true;try{const response=await fetch(root.dataset.cleanupUrl,{method:'POST',headers:{'X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});const result=await response.json();if(!response.ok||!result.success)throw new Error(result.error||'Unable to clean expired sessions.');alertBox.className='alert alert-success';alertBox.textContent=`${result.cleaned_count||0} expired session${result.cleaned_count===1?'':'s'} cleaned.`;alertBox.focus();}catch(error){alertBox.className='alert alert-danger';alertBox.textContent=error.message;alertBox.focus();}finally{button.disabled=false;}});
})();
