# How to Screen Out VPS and International Respondents Using Qualtrics:  
**A Protocol**

Tyler Burleigh  
Data Cubed  
[tylerburleigh@gmail.com](mailto:tylerburleigh@gmail.com)

Ryan Kennedy  
University of Houston  
[rkennedy@uh.edu](mailto:rkennedy@uh.edu)

Scott Clifford  
University of Houston  
[scottaclifford@gmail.com](mailto:scottaclifford@gmail.com)

> **Note:** This protocol is a work in progress and we appreciate any feedback. As with any protocol, you should test it yourself before fielding.

If this protocol is useful in your research, we ask that you cite it to help others who might also find it useful. It can be cited as:

Burleigh, Tyler, Kennedy, Ryan and Clifford, Scott, How to Screen Out VPS and International Respondents Using Qualtrics: A Protocol (October 12, 2018). Available at SSRN: [https://ssrn.com/abstract=3265459](https://ssrn.com/abstract=3265459)

---

This protocol takes you through the steps of setting up a filter on Qualtrics that will block most people in a non-US location or using a Virtual Private Server (VPS) to cover their location. It will take you through all the steps, with illustrations as needed.

Before you begin, if you do not want people to be able to answer your survey more than once, you should always enable the Prevent Ballot Stuffing option in Survey Options.

> This can also be used to select only participants from other countries by simply changing the IP_countryCode parameter.

---

## Steps to Detect International and VPS Respondents

### 1. Create an Account on IP Hub

[https://iphub.info/pricing](https://iphub.info/pricing)

A free plan that allows for 1,000 requests per day should suffice for most research purposes, although larger plans are available. You will be given an API key that consists of about 50 random letters and numbers, looking something like this:

```
MxI5ODpZT2kmVnlsR5iMcjBrRWpjxVZOKXIRKU1sNmdZb30EMA==
```
*(This is not a real key, please do not try to use.)*

---

### 2. Add Embedded Data Fields in Qualtrics

Next, go to the Survey Flow of your Qualtrics survey. At the top of your survey, add an embedded data field with entries: IP, IP_countryCode, IP_countryName, IP_asn, IP_isp, IP_check, and IP_block. Then move this block to the top of your survey.

---

### 3. Add jQuery Library

Save the Survey Flow and go to the Look and Feel menu. In the Footer option, you will add a snippet to tell Qualtrics to include the jQuery library in your survey. You can find the most updated snippet here: [https://developers.google.com/speed/libraries/#jquery](https://developers.google.com/speed/libraries/#jquery)

As of this writing, you can also just paste in this snippet (version 3.3.1):

```html
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
```

---

### 4. Add a VPN/Ad Blocker Warning

Click Save. You will want to add a warning to the beginning of the survey to tell people who are in the U.S. to turn off their VPNs or any ad blocking software they are using. This will prevent you from receiving complaints from some Turkers. From our piloting, it also appears that this is an effective way to initially screen out people who you do not want to take the survey (we noticed a significant drop in the number of international IPs testing our system once we added the warning).

> **Warning!**
>
> This survey uses a protocol to check that you are responding from inside the U.S. and not using a Virtual Private Server (VPS), Virtual Private Network (VPN), or proxy to hide your country. In order to take this survey, please turn off your VPS/VPN/proxy if you are using one and also any ad blocking applications. Failure to do this might prevent you from completing the HIT.
>
> For more information on why we are requesting this, see this post from TurkPrime (https://goo.gl/WD6QD4)

---

### 5. Add JavaScript to the Consent/Intro Page

Then go to the second element in your survey (the screen after the warning message—usually the consent script or study introduction). Click on the question options gear and select "Add JavaScript." Delete the default script and replace it with the script below (or it can be found here: [https://gist.github.com/tylerburleigh/64641a79ce73995740cd629ba7f7b48f](https://gist.github.com/tylerburleigh/64641a79ce73995740cd629ba7f7b48f)). Be sure to replace `PUT_YOUR_API_KEY_HERE` with your API key for IP Hub.

```javascript
Qualtrics.SurveyEngine.addOnload(function() {
  jQuery(function() {
    var request = $.ajax({
      url: "https://ipcheck.dynu.net/s/ipCheck.php",
      type: "POST",
      data: {API : "PUT_YOUR_API_KEY_HERE"}
    });

    request.done(function(msg) {
      obj = JSON.parse(msg);
      Qualtrics.SurveyEngine.setEmbeddedData('IP', obj.ip);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_countryCode', obj.countryCode);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_countryName', obj.countryName);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_asn', obj.asn);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_isp', obj.isp);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_block', obj.block);
      Qualtrics.SurveyEngine.setEmbeddedData('IP_check', "success");
    });

    request.fail(function(jqXHR, textStatus) {
      Qualtrics.SurveyEngine.setEmbeddedData('IP_check', "error");
    });
  });
});
```

---

### 6. PHP Function for IP Check (Optional)

[If you are fine with using our site to host the PHP, you do not need to take any action in this step.] This JavaScript calls a PHP function hosted at:  
[https://ipcheck.dynu.net/s/ipCheck.php](https://ipcheck.dynu.net/s/ipCheck.php)

You can also copy the code from this site ([https://gist.github.com/tylerburleigh/a93a6e8c50e8af1279736207b56acb5d](https://gist.github.com/tylerburleigh/a93a6e8c50e8af1279736207b56acb5d)), or below, and host it on your preferred site.

```php
<?php
// allow CORS, otherwise it will complain
header("Access-Control-Allow-Origin: *");

// This function is from https://stackoverflow.com/a/48882693/7889212
function getIP($ip = null, $deep_detect = TRUE){
  if (filter_var($ip, FILTER_VALIDATE_IP) === FALSE) {
    $ip = $_SERVER["REMOTE_ADDR"];
    if ($deep_detect) {
      if (filter_var(@$_SERVER['HTTP_X_FORWARDED_FOR'], FILTER_VALIDATE_IP))
        $ip = $_SERVER['HTTP_X_FORWARDED_FOR'];
      if (filter_var(@$_SERVER['HTTP_CLIENT_IP'], FILTER_VALIDATE_IP))
        $ip = $_SERVER['HTTP_CLIENT_IP'];
    }
  } else {
    $ip = $_SERVER["REMOTE_ADDR"];
  }
  return $ip;
}

// receive POST
$API = $_POST["API"];
$IP = getIP();

// create curl resource
$ch = curl_init();

// set API key header
$headers = array('X-Key: ' . $API);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

// set url
curl_setopt($ch, CURLOPT_URL, "http://v2.api.iphub.info/ip/".$IP);

// return the transfer as a string
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);

// $output contains the output string
$output = curl_exec($ch);

echo $output;

// close curl
curl_close($ch);
?>
```

---

### 7. Add a Timer to the JavaScript Page

You will also want to set a timer on the same block and page that includes the JavaScript. If a user runs through the page too quickly and the script does not have time to get a response, it may not work. You can add a timer by adding a new question and selecting a Timing question. You will then change the “Enable submit time after (seconds)” option. We found that 20 seconds is a safe amount of time. We also recommend telling participants about the pause, with something like, “The Next arrow will appear in a little bit. Please review the information on this page carefully.”

---

### 8. Add Warning Messages

This will ensure that the embedded data parameters we set at the top of the survey make it into the actual survey. If you would like to screen out international or VPS actors, you can do this using the next few steps. Begin by setting up warnings explaining why they are not allowed to take the survey. These can be added as descriptive text questions in their own Block (or text entry questions if using the appeals procedure described at the end). This is both courteous and will prevent you from getting nasty emails. Below are the ones we used.

#### VPS Warning

> **Our system has detected that you are using a Virtual Private Server (VPS) or proxy to mask your country location.** As has been widely reported, this has caused a number of problems with MTurk data (https://goo.gl/WD6QD4).
>
> Because of this, we cannot let you participate in this study. If you are located in the U.S., please turn off your VPS the next time you participate in a survey-based HIT, as we requested in the warning message at the beginning. If you are outside of the U.S., we apologize, but this study is directed only towards U.S. Participants.
>
> Thank you for your interest in our study.

#### Out of US Warning

> **Our system has detected that you are attempting to take this survey from a location outside of the U.S.** Unfortunately, this study is directed only towards participants in the U.S. and we cannot accept responses from those in other countries (as per our IRB protocol).
>
> Thank you for your interest in our study.

#### Still Missing Warning

*(This message is added defensively—steps have been taken to ensure ad blockers or quick responses do not affect the protocol. In our pilot, we find a small number of cases (about 1.6%) where the JavaScript does not return information and they need to be checked after the survey is complete):*

> **For some reason we were still unable to verify your country location.** We ask you to please assist us in getting this protocol correct. Please enter your MTurk worker ID below and contact the requester for this HIT to report the problem.
>
> Once you click Next, you will be taken to the survey (and certifying that you are taking this survey from the U.S. and not using a VPS). We will be checking locations manually for those who reach this point and you will be contacted if this check identifies you as violating these requirements.

---

### 9. Set Up Branch Logic in Survey Flow

Now go back to the Survey Flow. After the first question, add two Branches that respond to Embedded Data.

- For the first one, set it to activate “If IP_block is Equal to 1”. Move your VPS warning text underneath this branch and then add an End of Survey option below it.
- For the second Branch, set it to activate “If IP_countryCode is Not Equal to US”, then create two sub-Branches for “If IP_countryCode is Not Empty” and “If IP_countryCode is Empty”. Drag your out of US warning underneath under the first sub-Branch and add an End of Survey option below it. Under your second sub-Branch where IP_countryCode is empty (this means that there was an error in the IP trace) drag your location missing warning.

Now if anyone tries to access your survey from outside the US or from a server farm, they will be shown a warning and taken to the end of your survey. This part of your survey flow will look like the illustration below.

---

### 10. Save the New Survey Flow

Now nobody (or at least very few people) outside of the US or using a detected server farm should be able to take your survey.

---

#### Final Note: Appeals Process

[One final note. Although we did not run into this problem in the pilot of this protocol, there is always the possibility of false positives—people who are screened out that should not have been. When we used this protocol, we also included an appeal process for Turkers. We added to the information screens shown above the line:

> “If you have received this message in error, please contact the requester and enter your MTurk worker ID in the box below”

and added a text box for entry (see illustration below). While several did enter their worker IDs, we have yet to receive a contact following up to appeal their exclusion.]

#### VPS Exclusion Message with Appeal Process

> **Our system has detected that you are using a Virtual Private Server (VPS) or proxy to mask your country location.** As has been widely reported, this has caused a number of problems with MTurk data (https://goo.gl/WD6QD4).
>
> Because of this, we cannot let you participate in this study. If you are located in the U.S., please turn off your VPS the next time you participate in a survey-based HIT, as we requested in the warning message at the beginning. If you are outside of the U.S., we apologize, but this study is directed only towards U.S. Participants.
>
> Thank you for your interest in our study.
>
> If you have received this message in error, please report it to the requester for this study and enter your MTurk Worker ID below.

---

## References

[1] Burleigh, Tyler, Kennedy, Ryan and Clifford, Scott, How to Screen Out VPS and International Respondents Using Qualtrics: A Protocol (October 12, 2018). Available at SSRN: [https://ssrn.com/abstract=3265459](https://ssrn.com/abstract=3265459)