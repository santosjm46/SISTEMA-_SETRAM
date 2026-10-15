const sidebar = document.getElementById('sidebar');
const shade = document.getElementById('sidebarShade');
const account = document.createElement('a');
account.className = 'nav-item';
account.href = '/perfil/clave/';
account.textContent = 'Mi cuenta · Cambiar contraseña';
sidebar?.querySelector('nav')?.append(account);
document.getElementById('menuToggle')?.addEventListener('click', () => {
  sidebar?.classList.toggle('open'); shade?.classList.toggle('show');
  document.getElementById('menuToggle')?.setAttribute('aria-expanded',sidebar?.classList.contains('open')?'true':'false');
});
shade?.addEventListener('click', () => {sidebar?.classList.remove('open'); shade.classList.remove('show');});
document.getElementById('recordForm')?.addEventListener('submit', event => {
  const button = event.currentTarget.querySelector('button[type="submit"]');
  if (button) {button.disabled = true; button.textContent = 'Guardando…';}
});
if (location.pathname.includes('/inspecciones/nuevo/') || location.pathname.includes('/informes_inspeccion/nuevo/')) {
  document.getElementById('id_checklist')?.addEventListener('change', event => {
    const target = new URL(location.href);
    target.searchParams.set('plantilla', event.target.value);
    location.assign(target);
  });
}

document.querySelectorAll('.data-chart').forEach(chart => {
  const rows=[...chart.querySelectorAll('.chart-row')];
  const values=rows.map(row=>Number((row.dataset.value||'0').replace(/\s/g,'').replace(',','.'))||0);
  const max=Math.max(...values,1);
  rows.forEach((row,i)=>{row.querySelector('.chart-track span').style.width=(100*values[i]/max)+'%';row.title=row.textContent.trim();});
});

const checklist=[...document.querySelectorAll('select[name^="item_"]')];
function inspectionProgress(){
  const complete=checklist.filter(field=>field.value).length;
  const failures=checklist.filter(field=>['critico','defecto'].includes(field.value)).length;
  const node=document.getElementById('inspectionProgress');
  if(node)node.textContent=complete+'/'+checklist.length+' puntos respondidos · '+failures+' hallazgos';
}
checklist.forEach(field=>field.addEventListener('change',inspectionProgress));
document.getElementById('passAll')?.addEventListener('click',()=>{checklist.forEach(field=>{field.value='aprobado';});inspectionProgress();});
inspectionProgress();

document.querySelectorAll('select[data-failure-options]').forEach(select=>{
  const options=JSON.parse(select.dataset.failureOptions);
  select.addEventListener('change',()=>{
    const item=options[select.value];if(!item)return;
    const form=select.form;
    for(const [name,value] of [['title',item.name],['description',item.description]]){
      const input=form.elements.namedItem(name);
      if(input&&!input.value.trim())input.value=value;
    }
    const system=form.elements.namedItem('failure_category');if(system)system.value=item.system;
  });
});

const preferenceData=document.getElementById('dashboardWidgets');
if(preferenceData){
  const visible=JSON.parse(preferenceData.textContent);
  document.querySelectorAll('[data-widget]').forEach(node=>{
    if(!visible.includes(node.dataset.widget)){
      const container=node.closest('[class*="col-"]');(container||node).hidden=true;
    }
  });
}

const wizard=document.querySelector('form[data-wizard="true"]');
if(wizard){
  wizard.noValidate=true;
  const sections=[...wizard.querySelectorAll('.wizard-section')];
  const steps=[...wizard.querySelectorAll('.wizard-step')];
  const save=wizard.querySelector('button[type="submit"]');
  let active=Math.max(0,sections.findIndex(section=>section.querySelector('.field-error')));
  function review(){
    const node=document.getElementById('wizardReview');node.replaceChildren();
    for(const field of wizard.elements){
      if(!field.name||['_token','csrfmiddlewaretoken'].includes(field.name)||field.type==='password')continue;
      const label=field.labels?.[0]?.textContent.trim();if(!label)continue;
      const value=field.tagName==='SELECT'?[...field.selectedOptions].map(option=>option.text).join(', '):field.type==='checkbox'?(field.checked?'Sí':'No'):field.value;
      if(!value)continue;
      const item=document.createElement('div'),title=document.createElement('dt'),detail=document.createElement('dd');
      title.textContent=label;detail.textContent=value;item.append(title,detail);node.append(item);
    }
  }
  function show(index){
    active=Math.max(0,Math.min(index,sections.length-1));
    sections.forEach((section,i)=>section.hidden=i!==active);
    steps.forEach((step,i)=>step.classList.toggle('active',i===active));
    document.getElementById('wizardPrevious').disabled=active===0;
    document.getElementById('wizardNext').hidden=active===sections.length-1;
    save.hidden=active!==sections.length-1;
    if(active===sections.length-1)review();
  }
  function next(){
    for(const field of sections[active].querySelectorAll('input,select,textarea')){
      if(!field.checkValidity()){field.reportValidity();return;}
    }
    show(active+1);
  }
  steps.forEach((step,i)=>step.addEventListener('click',()=>show(i)));
  document.getElementById('wizardNext').addEventListener('click',next);
  document.getElementById('wizardPrevious').addEventListener('click',()=>show(active-1));
  wizard.addEventListener('keydown',event=>{if(event.key==='Enter'&&event.target.tagName!=='TEXTAREA'&&active<sections.length-1){event.preventDefault();next();}});
  wizard.addEventListener('submit',event=>{
    for(let i=0;i<sections.length;i++)for(const field of sections[i].querySelectorAll('input,select,textarea')){
      if(!field.checkValidity()){event.preventDefault();show(i);field.reportValidity();save.disabled=false;save.textContent='Guardar registro';return;}
    }
  });
  show(active);
}
