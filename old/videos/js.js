var videoEnded = 0;
	
$(document).ready(function() {
	var myPlayer = videojs('vid1');
	
	
	// stuff
	myPlayer.ready(function(){
		var player = this;
		
		// Detect video ended
		player.on('ended', function() {
			videoEnded = 1;
			sendMessage('videoEnd');
		});
	});
	
	
	// addEventListener support for IE8
	function bindEvent(element, eventName, eventHandler) {
		if (element.addEventListener) {
			element.addEventListener(eventName, eventHandler, false);
		} else if (element.attachEvent) {
			element.attachEvent('on' + eventName, eventHandler);
		}
	}
	// Send a message to the parent
	var sendMessage = function (msg) {
		// Make sure you are sending a string, and to stringify JSON
		window.parent.postMessage(msg, '*');
	};
	

	function isFocused() {
		return document.hasFocus();
	}
	
	// Listen to messages from parent window
	bindEvent(window, 'message', function (e) {
		if(e.data == false && isFocused() == false)
			myPlayer.pause();
	});
	
	
});