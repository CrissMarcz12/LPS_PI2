import { LocalHandCamera } from "./recognition.js";

const $ = id => document.getElementById(id); let camera, capturing = false, testing = false, minimum = 20, intervalMs = 100;
const api = async (path, options = {}) => { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(data.message || "No se pudo completar la acción."); return data; };
const json = body => ({method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
const label = () => $("training-label").value.trim();
function status(message, error = false) { $("training-notice").textContent = message; $("training-notice").className = error ? "error" : ""; }
function showTestResult(data) {
  const result = $("training-test-result"), button = $("test-model");
  button.textContent = testing ? "■ DETENER PRUEBA" : "▶ PROBAR MI SEÑA";
  if (!testing) { result.textContent = data?.modelReady ? "Modelo listo. Pulsa PROBAR MI SEÑA." : "Entrena este modelo para habilitar la prueba."; result.dataset.state = "idle"; return; }
  if (!data?.modelReady) { result.textContent = "Aún no hay un modelo entrenado para probar."; result.dataset.state = "error"; return; }
  if (!data.handDetected) { result.textContent = "Coloca una mano completa frente a la cámara."; result.dataset.state = "idle"; return; }
  const detected = data.stablePrediction || data.prediction;
  if (data.stable && detected === label()) { result.textContent = `✓ ¡Bien entrenada! Reconoció ${detected}.`; result.dataset.state = "success"; return; }
  if (detected && detected !== label()) { result.textContent = `✕ Reconoció ${detected}; vuelve a capturar ${label()} con más variedad.`; result.dataset.state = "error"; return; }
  result.textContent = "Analizando tu seña… mantenla estable un instante."; result.dataset.state = "idle";
}
function drawCounts(counts) {
  const holder=$("letter-counts"), selector=$("trained-label-select"), labels=Object.keys(counts).sort();
  holder.replaceChildren(); selector.replaceChildren();
  const placeholder=document.createElement("option"); placeholder.value=""; placeholder.textContent="Selecciona una letra entrenada"; selector.append(placeholder);
  if(!labels.length){holder.textContent="Aún no hay muestras."; selector.disabled=true; return;}
  selector.disabled=false;
  for(const item of labels){
    const chip=document.createElement("span"), count=document.createElement("b"), option=document.createElement("option");
    chip.append(document.createTextNode(item)); count.textContent=counts[item]; chip.append(count); holder.append(chip);
    option.value=item; option.textContent=`${item} · ${counts[item]} muestras`; selector.append(option);
  }
  if(labels.includes(label())) selector.value=label();
}
function setCameraStatus(active, message) { $("training-dot").classList.toggle("active",active); $("training-camera-status").textContent=message; $("training-message").classList.toggle("hidden",active); if(!active) $("training-message").textContent=message; }
function referenceUrl() { return `/references/${encodeURIComponent(label())}.png?t=${Date.now()}`; }
function refreshReference() { const preview=$("training-reference-preview"); preview.src=referenceUrl(); preview.hidden=false; preview.onerror=()=>{preview.hidden=true;}; }
async function configure(active = capturing) { const data = await api("/api/training/configure",json({label:label(),capturing:active})); $("training-label").value=data.label; $("training-count").textContent=`${data.sampleCount} / ${minimum} muestras`; refreshReference(); return data; }
async function startCamera() { await configure(false); camera?.stop(); camera = new LocalHandCamera($("training-camera"),$("training-landmarks"), data => { $("training-hand").textContent=data.handDetected ? `✓ Mano detectada · ${data.framesCollected}/20 frames` : "⚠ Mano no detectada"; $("training-count").textContent=`${data.sampleCount} / ${minimum} muestras`; $("training-prediction").textContent=data.prediction||"—"; $("training-confidence").textContent=data.confidence==null?"":` · ${data.confidence}%`; showTestResult(data); if(data.saved) status("Muestra guardada."); }, () => setCameraStatus(false,"No se pudo usar la cámara."), payload => api("/api/training/landmarks",json(payload)), intervalMs); const active=await camera.start(); setCameraStatus(active,active?"Cámara activa":"Permite el acceso a la cámara"); }
async function refresh() { const data=await api("/api/training"); minimum=data.minimumSamples; intervalMs=data.recognitionIntervalMs||100; drawCounts(data.counts); await configure(false); }
$("capture-toggle").addEventListener("click",async()=>{testing=false;capturing=true;await configure(true);showTestResult();status("● CAPTURANDO: mueve levemente la mano entre muestras.");});
$("stop-capture").addEventListener("click",async()=>{capturing=false;await configure(false);status("Captura detenida.");});
$("training-label").addEventListener("change",async()=>{capturing=false;testing=false;try{await refresh();showTestResult();}catch(error){status(error.message,true);}});
$("training-label").addEventListener("keydown",event=>{if(event.key==="Enter") $("training-label").dispatchEvent(new Event("change"));});
$("trained-label-select").addEventListener("change",async event=>{if(!event.target.value)return;$("training-label").value=event.target.value;$("training-label").dispatchEvent(new Event("change"));});
$("training-reference").addEventListener("change",async event=>{const image=event.target.files[0];if(!image)return;try{const form=new FormData();form.append("label",label());form.append("image",image,image.name);const data=await api("/api/training/reference",{method:"POST",body:form});$("training-label").value=data.label;refreshReference();status("Referencia visual guardada.");}catch(error){status(error.message,true);}finally{event.target.value="";}});
$("train-model").addEventListener("click",async()=>{const data=await api("/api/training/train",json({label:label()}));status(data.message,!data.success);await refresh();showTestResult({modelReady:data.success});});
$("test-model").addEventListener("click",async()=>{testing=!testing;capturing=false;await configure(false);showTestResult();status(testing?"Prueba activa: muestra la seña frente a la cámara.":"Prueba detenida.");});
$("clear-samples").addEventListener("click",async()=>{if(!confirm("¿Borrar las muestras y el modelo de esta etiqueta? La imagen de referencia se conservará."))return;testing=false;const data=await api("/api/training/clear",json({label:label()}));status(data.modelRemoved?`Se eliminaron ${data.removed} muestras y el modelo de ${label()}.`:`No había modelo ni muestras para ${label()}.`);await refresh();showTestResult({modelReady:false});});
try{await refresh();showTestResult();await startCamera();}catch(error){console.error(error);status(error.message,true);}
