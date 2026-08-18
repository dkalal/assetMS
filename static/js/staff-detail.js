(function(){
  'use strict';
  const root=document.querySelector('[data-staff-profile]');
  if(!root)return;
  const csrf=document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
  document.querySelector('[data-print-page]')?.addEventListener('click',()=>window.print());
  const editForm=document.getElementById('editProfileForm');
  if(editForm){
    const alertBox=document.getElementById('editProfileAlert');
    const active=document.getElementById('editIsActive');
    const reasonWrap=document.querySelector('[data-status-reason]');
    const reason=document.getElementById('statusChangeReason');
    const button=document.getElementById('saveProfileButton');
    const originalStatus=root.dataset.originalStatus==='true';
    const showEditError=message=>{alertBox.className='alert alert-danger';alertBox.textContent=message;alertBox.focus();};
    function syncReason(){const changed=active.checked!==originalStatus;reasonWrap.classList.toggle('d-none',!changed);reason.required=changed;if(!changed)reason.value='';}
    async function saveProfile(event){
      event.preventDefault();syncReason();
      if(!editForm.checkValidity()){editForm.classList.add('was-validated');editForm.reportValidity();return;}
      const payload={first_name:document.getElementById('editFirstName').value.trim(),last_name:document.getElementById('editLastName').value.trim(),email:document.getElementById('editEmail').value.trim(),phone_number:document.getElementById('editPhone').value.trim(),role:document.getElementById('editRole').value,is_active:active.checked};
      if(active.checked!==originalStatus)payload.status_change_reason=reason.value.trim();
      button.disabled=true;button.querySelector('.button-label').textContent='Saving…';
      try{const response=await fetch(root.dataset.updateUrl,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify(payload)});const result=await response.json();if(!response.ok||!result.success)throw new Error(result.error||'Unable to update user.');window.location.reload();}
      catch(error){showEditError(error.message);button.disabled=false;button.querySelector('.button-label').textContent='Save changes';}
    }
    active.addEventListener('change',syncReason);editForm.addEventListener('submit',saveProfile);syncReason();
  }
  const transferModal=document.getElementById('bulkTransferModal');
  const transferForm=document.getElementById('bulkTransferForm');
  if(!transferModal||!transferForm)return;
  const recipient=document.getElementById('transferToUser');
  const userStatus=document.getElementById('transferUserStatus');
  const transferAlert=document.getElementById('bulkTransferAlert');
  const transferButton=document.getElementById('executeTransferButton');
  const assetRows=Array.from(document.querySelectorAll('[data-transfer-asset]'));
  const progressWrap=document.querySelector('[data-transfer-progress-wrap]');
  const progress=document.querySelector('[data-transfer-progress]');
  const progressBar=progress?.closest('[role=progressbar]');
  const progressLabel=document.querySelector('[data-transfer-progress-label]');
  const progressCount=document.querySelector('[data-transfer-progress-count]');
  let usersLoaded=false;
  const showTransferMessage=(message,kind='danger')=>{transferAlert.className=`alert alert-${kind}`;transferAlert.textContent=message;transferAlert.focus();};
  async function loadUsers(){
    if(usersLoaded)return;recipient.disabled=true;userStatus.textContent='Loading eligible users…';
    try{const response=await fetch(root.dataset.usersUrl,{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});const result=await response.json();if(!response.ok||!result.success)throw new Error(result.error||'Unable to load users.');const users=(result.users||[]).filter(user=>user.id!==Number(root.dataset.staffId)&&user.is_active);recipient.replaceChildren(new Option('Select user',''));users.forEach(user=>recipient.add(new Option(`${user.first_name||''} ${user.last_name||''}`.trim()||user.username,user.id)));userStatus.textContent=users.length?'':'No eligible active users are available.';recipient.disabled=false;usersLoaded=true;}catch(error){userStatus.textContent=error.message;showTransferMessage(error.message);}
  }
  async function executeTransfers(event){
    event.preventDefault();
    if(!transferForm.checkValidity()){transferForm.classList.add('was-validated');transferForm.reportValidity();return;}
    const rowsToProcess=assetRows.filter(row=>row.querySelector('[data-transfer-asset-status]')?.textContent!=='Requested');
    const selectedName=recipient.selectedOptions[0]?.textContent||'the selected user';
    if(!window.confirm(`Initiate ${rowsToProcess.length} transfer request${rowsToProcess.length===1?'':'s'} to ${selectedName}?`))return;
    transferButton.disabled=true;transferButton.querySelector('.button-label').textContent='Processing…';progressWrap.classList.remove('d-none');
    let completed=0;let failed=0;
    for(const row of rowsToProcess){
      try{const response=await fetch(root.dataset.transferUrl,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify({asset_id:Number(row.dataset.assetId),to_user_id:Number(recipient.value),initiator_comment:document.getElementById('transferReason').value.trim()})});const result=await response.json();if(!response.ok||!result.success)throw new Error(result.error||result.errors||'Request failed.');completed+=1;const badge=row.querySelector('[data-transfer-asset-status]');badge.className='status-badge status-badge--completed';badge.textContent='Requested';}catch(error){failed+=1;const badge=row.querySelector('[data-transfer-asset-status]');badge.className='status-badge status-badge--damaged';badge.textContent='Failed';}
      const processed=completed+failed;const percentage=Math.round(processed/rowsToProcess.length*100);progress.style.width=`${percentage}%`;progressBar.setAttribute('aria-valuenow',String(percentage));progressLabel.textContent=processed===rowsToProcess.length?'Finished':'Processing transfers…';progressCount.textContent=`${processed}/${rowsToProcess.length}`;
    }
    if(failed===0){showTransferMessage(`${completed} transfer request${completed===1?'':'s'} initiated. The receiver must now review them.`,'success');transferButton.classList.add('d-none');}
    else{showTransferMessage(`${completed} request${completed===1?'':'s'} initiated; ${failed} failed. Review the marked assets before retrying.`,'warning');transferButton.disabled=false;transferButton.querySelector('.button-label').textContent='Retry failed transfers';}
  }
  transferModal.addEventListener('show.bs.modal',loadUsers);transferForm.addEventListener('submit',executeTransfers);
})();
