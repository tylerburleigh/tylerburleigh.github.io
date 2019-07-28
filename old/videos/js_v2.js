var videoEnded = 0;

const plyr = new Plyr("#player", {
controls: ['play-large', 'play', 'current-time', 'fullscreen'],
listeners: {
  seek: function customSeekBehavior(e) {
    var currentTime = plyr.currentTime;
    var newTime = _getTargetTime(plyr, e);
    // We only want rewind functionality
    // Therefore, disallow moving forward
    if (newTime > currentTime) {
      // Works if we add the following:
      // Object.defineProperty(event, "defaultPrevented", {
      //   value: event.defaultPrevented,
      //   writable: true
      // });
      // event.preventDefault = () => {
      //   event.defaultPrevented = true;
      // };
      e.preventDefault();
      console.log(`prevented`);
      return false;
    }
  }
}
});

// This code was pulled from plyr v2
// There's probably a much nicer way of doing this
function _getTargetTime(plyr, input) {
	if (
	  typeof input === "object" &&
	  (input.type === "input" || input.type === "change")
	) {
	  return input.target.value / input.target.max * plyr.media.duration;
	} else {
	  // We're assuming its a number
	  return Number(input);
	}
}
	
$(document).ready(function() {


  // Detect video ended
  plyr.on('ended', function() {
    videoEnded = 1;
    sendMessage('videoEnd');
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
			plyr.pause();
	});
	
	
});
