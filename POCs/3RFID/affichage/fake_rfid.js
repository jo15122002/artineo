
// Send message to server every 5 seconds
setInterval(() => {
    ws.send(JSON.stringify({"module":3, "action":"set", "data":{
        "uid1": "880424973f",
        "uid2": "8804d091cd",
        "uid3": "8804fa8cfa",
        "current_set": 1,
        "button_pressed": true
    }}));
    console.log('Message sent to server');
    }, 5000);
