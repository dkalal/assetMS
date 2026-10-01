(function(){
  'use strict';
  const modal=document.getElementById('createUserModal');
  const form=document.getElementById('createUserForm');
  if(!modal||!form||modal.dataset.initialized==='true')return;
  modal.dataset.initialized='true';
  const submit=document.getElementById('submitCreateUser');
  const alertBox=document.getElementById('userCreateAlert');
  const branchSelect=document.getElementById('primaryBranch');
  const branchStatus=document.getElementById('branchLoadStatus');
  const passwordOne=document.getElementById('password1');
  const passwordTwo=document.getElementById('password2');
  const csrf=form.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
  const showAlert=(message,kind='danger')=>{alertBox.className=`alert alert-${kind}`;alertBox.textContent=message;alertBox.focus();};
  async function loadBranches(){
    branchSelect.disabled=true;branchStatus.textContent='Loading branches…';
    try{
      const response=await fetch(modal.dataset.branchesUrl,{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error||'Unable to load branches.');
      branchSelect.replaceChildren(new Option('Select branch',''));
      (data.branches||[]).forEach(branch=>{const option=new Option(`${branch.name}${branch.code?` (${branch.code})`:''}`,branch.id);option.disabled=branch.is_active===false;branchSelect.add(option);});
      branchStatus.textContent=data.branches?.length?'':'No active branches are available.';branchSelect.disabled=false;
    }catch(error){branchStatus.textContent=error.message;showAlert(error.message);}
  }
  function validatePasswords(){const mismatch=passwordOne.value&&passwordTwo.value&&passwordOne.value!==passwordTwo.value;passwordTwo.setCustomValidity(mismatch?'Passwords do not match.':'');}
  async function createUser(event){
    event.preventDefault();validatePasswords();
    if(!form.checkValidity()){form.classList.add('was-validated');form.reportValidity();return;}
    submit.disabled=true;submit.querySelector('.button-label').textContent='Creating…';
    const data=Object.fromEntries(new FormData(form).entries());
    data.send_invitation=document.getElementById('sendInvitation').checked;
    data.force_password_change=document.getElementById('forcePasswordChange').checked;
    if(!data.password1){delete data.password1;delete data.password2;}
    try{
      const response=await fetch(modal.dataset.createUrl,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify(data)});
      const result=await response.json();
      if(!response.ok||!result.success){const errors=result.errors&&typeof result.errors==='object'?Object.values(result.errors).flat().join(' '):'';throw new Error(errors||result.details||result.error||'Unable to create user.');}
      bootstrap.Modal.getInstance(modal)?.hide();
      const content=document.getElementById('passwordDisplayContent');content.replaceChildren();
      const details=document.createElement('dl');details.className='row mb-0';
      [['Name',result.user.full_name],['Username',result.user.username],['Role',result.user.role_display],['Branch',result.user.primary_branch_name],['Temporary password',result.temporary_password]].forEach(([label,value])=>{if(!value)return;const dt=document.createElement('dt');dt.className='col-sm-5';dt.textContent=label;const dd=document.createElement('dd');dd.className='col-sm-7';dd.textContent=value;details.append(dt,dd);});
      content.append(details);
      const successModal=document.getElementById('passwordDisplayModal');successModal.addEventListener('hidden.bs.modal',()=>window.location.reload(),{once:true});bootstrap.Modal.getOrCreateInstance(successModal).show();
    }catch(error){showAlert(error.message);}finally{submit.disabled=false;submit.querySelector('.button-label').textContent='Create user';}
  }
  modal.addEventListener('show.bs.modal',loadBranches);
  modal.addEventListener('hidden.bs.modal',()=>{form.reset();form.classList.remove('was-validated');alertBox.className='alert d-none';});
  passwordOne.addEventListener('input',validatePasswords);passwordTwo.addEventListener('input',validatePasswords);form.addEventListener('submit',createUser);
})();
