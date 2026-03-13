async function updateEmotion(){

let response = await fetch("/emotion")

let data = await response.json()

document.getElementById("emotion").innerText = data.emotion

let tips=document.getElementById("tips")

tips.innerHTML=""

data.tips.forEach(t=>{
let li=document.createElement("li")
li.innerText=t
tips.appendChild(li)
})

}

setInterval(updateEmotion,2000)