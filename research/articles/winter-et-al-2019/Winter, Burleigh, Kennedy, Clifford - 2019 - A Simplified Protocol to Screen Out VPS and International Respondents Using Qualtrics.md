# A Simplified Protocol to Screen Out VPS and International Respondents Using Qualtrics

Nicholas J. G. Winter  
University of Virginia  
[nwinter@virginia.edu](mailto:nwinter@virginia.edu)

Tyler Burleigh  
Data Cubed  
[tylerburleigh@gmail.com](mailto:tylerburleigh@gmail.com)

Ryan Kennedy  
University of Houston  
[rkennedy@uh.edu](mailto:rkennedy@uh.edu)

Scott Clifford  
University of Houston  
[scottaclifford@gmail.com](mailto:scottaclifford@gmail.com)

---

> **Note:** This protocol is a work in progress and we appreciate any feedback. As with any protocol, you should test it yourself before fielding.

If this protocol is useful in your research, we ask that you cite it to help others who might also find it useful. It can be cited as:

> Winter, Nicholas J. G., Burleigh, Tyler, Kennedy, Ryan and Clifford, Scott, A Simplified Protocol to Screen Out VPS and International Respondents Using Qualtrics (February 1, 2019). Available at SSRN: [https://ssrn.com/abstract=3327274](https://ssrn.com/abstract=3327274)

---

This protocol takes you through the steps of setting up a filter on Qualtrics that will block most people in a non-US location or using a Virtual Private Server (VPS) to cover their location. It will take you through all the steps, with illustrations as needed.

Before you begin, if you do not want people to be able to answer your survey more than once, you should always enable the **Prevent Ballot Stuffing** option in Survey Options.

This option places a cookie on the user’s browser to prevent them from answering the survey more than once from the same browser. It does not completely prevent duplicate responses, since users can take steps to erase or avoid detection through cookies. But it is a useful supplement to MTurk’s built-in checks to avoid duplication.

> *This can also be used to select only participants from other countries by simply changing the IP_countryCode parameter.*

---

## Steps to Detect International and VPS Respondents

The main concept is to look up the IP address using a security service and use that information to make decisions on how to handle the potential respondent.

### 1. Create an Account on IP Hub

Go to [IP Hub](https://iphub.info/pricing). A free plan that allows for 1,000 requests per day should suffice for most research purposes, although larger plans are available. We recommend IP Hub based on our own experiences, and because it provides a relatively liberal free service that functions quickly. You will be given an API key that consists of about 50 random letters and numbers, looking something like this:

```
MxI5ODpZT2kmVnlsR5iMcjBrRWpjxVZOKXIRKU1sNmdZb30EMA==
```

> *This is not a real key, please do not try to use.*

### 2. Add a Warning to the Beginning of the Survey

Tell people who are in the U.S. to turn off their VPNs or any ad blocking software they are using. This should be placed in its own block and should come before any other parts of the survey. This will prevent you from receiving complaints from some Turkers. From our piloting, it also appears that this is an effective way to initially screen out people who you do not want to take the survey (we noticed a significant drop in the number of international IPs testing our system once we added the warning).

### 3. Add a Web Service in Qualtrics Survey Flow

Go to the Survey Flow of your Qualtrics survey. After the block that contains the warning, add a Web Service.

### 4. Make the Call to IP Hub

In the “URL:” line, enter:

```
http://v2.api.iphub.info/ip/${loc://IPAddress}
```

The first part of this address calls the IP Hub API, the last part takes the IP address captured by Qualtrics and adds it to the API call. Make sure the “Method:” is set to “GET”.

### 5. Add a Custom Header

Click on “Add a custom header to send to web service…”  
On the left-hand side, for “Header to Web Service…” type in `X-Key`.  
On the right-hand side, where it says “Set a Value Now”, type in your API key.

### 6. Add Embedded Data

Click on “Add Embedded Data...” and add entries for `IP_block` and `IP_country` that correspond with the returned IP Hub fields `block` and `countryName`.

> *IP Hub also allows you to capture some other fields, including `countryCode`, `ASN`, and `ISP`. These may be useful for some analysts.*

### 7. Add Warning Messages

Set up warnings explaining why respondents are not allowed to take the survey. These can be added as descriptive text questions in their own Block (or text entry questions if using the appeals procedure described at the end). This is both courteous and will prevent you from getting nasty emails. Below are the ones we used.

#### VPS Warning

> **You are not eligible to take this survey.**  
> Our system has detected that you are using a VPN, VPS, or server farm. Please disable these services and try again.

#### Out of US Warning

> **You are not eligible to take this survey.**  
> Our system has detected that you are not located in the United States. This survey is only open to U.S. residents.

#### Still Missing Warning

This message is added defensively. We find a small number of cases (about 1.6% in our pilot) where the API lookup does not succeed and responses need to be checked after the survey is complete.

> **We are unable to verify your location.**  
> If you believe this is an error, please contact the requester.

### 8. Add Branches in Survey Flow

After the web service call, add two Branches that respond to Embedded Data.

- **First Branch:**  
  Set it to activate “If `IP_block` is Equal to 1”. This catches respondents who are identified as behind a VPS, VPN, or server farm. Move your VPS warning text underneath this branch and then add an End of Survey option below it.

- **Second Branch:**  
  Set it to activate “If `IP_country` is Not Equal to United States”.  
  Then create two sub-Branches:
    - One for “If `IP_country` is Not Empty”
    - Second for “If `IP_country` is Empty” (IP_country will be Empty if the IP trace failed for some reason.)

  Under the first sub-branch, drag your out of US warning and add an End of Survey option below it. Under the second sub-Branch, drag your location missing warning.

Now if anyone tries to access your survey from outside the US or from a server farm, they will be shown a warning and taken to the end of your survey. This part of your survey flow will look like the illustration below.

> *You may wish to create a Custom End of Survey Message in Qualtrics for these two End of Survey blocks, especially if your standard end of survey message includes the study debriefing and/or mTurk code. To do so, click “Customize” on the Block, then check “Override Survey Options,” and select “Custom end of survey message…” You can then choose a message from your Qualtrics Library or create a new one.*

### 9. Save the New Survey Flow

Now nobody (or at least very few people) outside of the US or using a detected server farm should be able to take your survey.

### 10. Handling False Positives: Appeal Process

With any IP lookup service, there is always a risk of false positives—people who get screened out when they should not have been. So far, we have only encountered two cases of this. But, because it can happen, and because those who report false positives are helping us evaluate the utility of the screening procedure, we also included an appeal process for Turkers.

We added to the information screens shown above the line:

> “If you have received this message in error, please contact the requester and enter your MTurk worker ID in the box below”

and added a text box for entry (see illustration below). In our case, the information provided to us about false positives from these respondents was worth paying them what they would have received for the survey, but this is left to the discretion of the researcher. With Amazon continuing to update their service and remove fraudulent participants, it is possible that one day the number of false positives will supersede the utility of this protocol, but we have, so far, continued to find it useful.

#### VPS Exclusion Message with Appeal Process

> **You are not eligible to take this survey.**  
> Our system has detected that you are using a VPN, VPS, or server farm. Please disable these services and try again.  
> If you have received this message in error, please contact the requester and enter your MTurk worker ID in the box below.

---

## References

[1] Winter, Nicholas J. G., Burleigh, Tyler, Kennedy, Ryan and Clifford, Scott, A Simplified Protocol to Screen Out VPS and International Respondents Using Qualtrics (February 1, 2019). Available at SSRN: [https://ssrn.com/abstract=3327274](https://ssrn.com/abstract=3327274)