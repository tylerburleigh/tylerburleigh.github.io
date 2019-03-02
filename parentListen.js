// addEventListener support for IE8
function bindEvent(element, eventName, eventHandler) {
	if (element.addEventListener){
		element.addEventListener(eventName, eventHandler, false);
	} else if (element.attachEvent) {
		element.attachEvent('on' + eventName, eventHandler);
	}
}

// Send a message to the child iframe
var sendMessage = function(msg) {
	// Make sure you are sending a string, and to stringify JSON
	if($("iframe").is(":visible"))
		$("iframe")[0].contentWindow.postMessage(msg, '*');
};

// Listen to message from child window
bindEvent(window, 'message', function (e) {
	if(e.data == "videoEnd")
		$("#NextButton").removeAttr("disabled");
});

setInterval(doThing, 100);
 
function doThing() {
	sendMessage(isFocused());
}

function isFocused() {
    return document.hasFocus();
}