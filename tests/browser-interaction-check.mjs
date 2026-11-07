const endpoint = process.env.R1_CDP_HTTP || 'http://127.0.0.1:9333'
const pages = await fetch(endpoint + '/json/list').then((response) => response.json())
const target = process.env.PANEL_URL || 'http://127.0.0.1:8080'
const page = pages.find((item) => item.type === 'page' && item.url.startsWith(target))
if (!page) throw new Error('No CDP page available')
const socket = new WebSocket(page.webSocketDebuggerUrl)
let sequence = 0
const pending = new Map()
function send(method, params = {}) {
  const id = ++sequence
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
}
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)) }
function evaluate(expression) {
  return send('Runtime.evaluate', { expression, returnByValue: true }).then((result) => result.result.value)
}
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (!message.id || !pending.has(message.id)) return
  const operation = pending.get(message.id)
  pending.delete(message.id)
  if (message.error) operation.reject(message.error)
  else operation.resolve(message.result)
})
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true })
  socket.addEventListener('error', reject, { once: true })
})
await send('Runtime.enable')
await wait(500)
const stateExpression = "({title:document.querySelector('.current-page-title')?.textContent,left:document.querySelector('.viewport')?.scrollLeft,width:document.querySelector('.viewport')?.clientWidth})"
const before = await evaluate(stateExpression)
await evaluate("document.querySelector('.page-arrow.previous').click()")
await wait(120)
const afterLeft = await evaluate(stateExpression)
await evaluate("document.querySelector('.page-arrow.next').click();document.querySelector('.page-arrow.next').click()")
await wait(120)
const afterRight = await evaluate(stateExpression)
await evaluate("document.querySelector('.viewport').scrollLeft=document.querySelector('.viewport').clientWidth")
await wait(100)
await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 330, y: 600, radiusX: 3, radiusY: 3, force: 1, id: 1 }] })
for (const x of [280, 220, 160, 100, 45]) {
  await send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: 600, radiusX: 3, radiusY: 3, force: 1, id: 1 }] })
  await wait(35)
}
await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
await wait(300)
const afterSwipe = await evaluate(stateExpression)
console.log(JSON.stringify({ before, afterLeft, afterRight, afterSwipe }, null, 2))
socket.close()
