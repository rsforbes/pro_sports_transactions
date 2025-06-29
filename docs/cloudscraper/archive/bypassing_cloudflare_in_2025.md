How to Bypass Cloudflare in 2025: The 9 Best Methods
Idowu Omisola
Idowu Omisola
Updated: February 13, 2025 · 14 min read
About 1/5 of websites you need to scrape use Cloudflare, a hardcore anti-bot protection system that gets you blocked easily. So what can you do?

We spent a million dollars figuring out how to bypass Cloudflare to write the most complete guide (you're reading it!). These are some of the techniques we'll cover:

Method #1: Use Cloudflare solvers.
Method #2: Web scraping API to bypass Cloudflare.
Method #3: Bypass Cloudflare CDN by calling the origin server.
Method #4: Implement fortified headless browsers.
Method #5: Smart proxies to get past Cloudflare.
Method #6: Bypass Cloudflare waiting room and reverse engineer its challenge.
Method #7: Cloudflare CAPTCHA bypass.
Method #8: Scrape Google cache.
Method #9: DYI Cloudflare bypass.
Let's roll!

What Is Cloudflare Bot Management
Cloudflare is a content delivery and web security company. It provides a Web Application Firewall (WAF) to defend websites against security threats, such as cross-site scripting (XSS), credential stuffing, and DDoS attacks.

One of the core systems of Cloudflare's WAF is the Bot Manager, which mitigates attacks from malicious bots without impacting real users. However, while Cloudflare allows known crawler bots like Google, it assumes that any unknown bot traffic, including web scrapers, is malicious.

So, your scraper may be denied access to a Cloudflare-protected web page regardless of your intent. If you've ever tried to scrape a Cloudflare-protected site, you might have run into a few of the following bot-manager-related errors:

Error 1003: Direct IP access not allowed.
Errors 1006, 1007, and 1008: Access denied.
Error 1009: Access denied due to your region.
Error 1010: Access denied due to suspicious browser signature.
Error 1015: Your access rate has been limited.
Error 1020: Access denied because your request looks malicious.
These challenges are often accompanied by a Cloudflare 403 Forbidden HTTP response status code.

How Does Cloudflare Detect Bots?
Cloudflare's detection method can be passive or active. Passive bot detection techniques use backend fingerprinting tests, while active detection techniques rely on client-side analyses. Let's dive into a few examples from each category.

Cloudflare Passive Bot Detection Techniques
Here's a non-exhaustive list of passive bot detection techniques that help Cloudflare detect web scrapers:

Detecting Botnets
Cloudflare ##maintains a catalog of devices, IP addresses, and behavioral patterns associated with malicious bot networks##. Any device suspected to belong to one of these networks is either automatically blocked or faced with additional client-side challenges to solve.

IP Address Reputation
A user's IP address reputation (also known as risk score or fraud score) is based on factors such as geolocation, ISP, and reputation history. For example, IPs belonging to a data center or known VPN provider will have a worse reputation than a residential IP address. A site may also choose to limit access to a site from regions outside of the area they serve since traffic from an actual customer should never come from there.

HTTP Request Headers
Cloudflare also uses the HTTP request headers to determine if you're a bot. For instance, if you use Python's Requests, you'll have a non-browser User Agent, such as python-requests/2.220. Cloudflare can easily flag and block your scraper with that User Agent, making a Cloudflare WAF bypass necessary for successful web scraping.

Your scraper can also get blocked if your request misses typical legitimate browser headers, has a header string mismatch, or contains an outdated header field. For example, including Sec-CH-UA-Full-Version-List in your headers when you've used a Firefox User Agent might get you blocked because Firefox doesn't support that header field.

TLS Fingerprinting
TLS fingerprinting enables Cloudflare's anti-bot to identify the client sending requests to a server. It's a powerful detection method because TLS implementation typically differs between operating systems, browsers, browser versions, and request-based libraries like Python's Requests.

For example, Chrome version 121 on Windows 10 has a different fingerprint than all of the following:

Chrome version 121 on Windows 8.
Chrome version 125 on Windows 10.
Firefox browser on Windows 10.
Chrome version 121 on an Android device.
The Python HTTP Requests library.
Although various TLS fingerprinting methods (such as JA3, JARM, and CYU) analyze different aspects of the TLS handshake, each technique consistently produces the same fingerprint for a given client configuration, even across subsequent requests.

The construction of a TLS fingerprint occurs during a client-server TLS Handshake. In this process, Cloudflare analyzes the "client hello" message fields, such as cipher suites, extensions, and elliptic curves, to compute a fingerprint hash for a given client.

It then looks up that hash in a database of pre-collected fingerprint hashes to determine the client sending the request. Once the client's hash matches an allowed fingerprint hash, Cloudflare further compares their User Agent headers.

If they match, the security system assumes that the request originated from a standard browser and grants access to the client. Otherwise, it flags the client as a bot and blocks it.

HTTP/2 Fingerprinting
The HTTP/2 specification extends the previous HTTP/1.1 protocol with new parameters to improve the performance of web applications with concurrency. Cloudflare's Bot Manager fingerprints these new values in upcoming requests to detect bot-like behavior.

One of the major HTTP/2 aspects fingerprinted by Cloudflare is the binary frame layer. It defines the payload exchanged between the client and the server.

In its whitepaper on Passive Fingerprinting of HTTP/2 Clients, Akamai proposes three fingerprinting methods. Here's the summary:

Frames: SETTINGS_HEADER_TABLE_SIZE, SETTINGS_ENABLE_PUSH, SETTINGS_MAX_CONCURRENT_STREAMS, SETTINGS_INITIAL_WINDOW_SIZE, SETTINGS_MAX_FRAME_SIZE, SETTINGS_MAX_HEADER_LIST_SIZE, WINDOW_UPDATE.
Stream Priority Information: StreamID:Exclusivity_Bit:Dependant_StreamID:Weight.
Pseudo Header Fields Order: The order of the pseudo-header fields must be :method, :authority, :scheme, and :path.
HTTP/2 fingerprinting method works similarly to TLS fingerprinting. The Bot Manager scans incoming HTTP/2 parameters against those in Cloudflare's fingerprint database to find a match. Both detection techniques work hand in hand.

Of all the passive bot detection techniques of Cloudflare, TLS and HTTP/2 fingerprinting are the most technically challenging to control in request-based bots.

However, they're also the most important to bypass. You must handle them properly, or you risk getting blocked!

Cloudflare Active Bot Detection Techniques
When you visit a Cloudflare-protected website via your local browser, checks are constantly running on the client side to determine if you're a robot. Here's a list of some of the active methods Cloudflare uses:

CAPTCHAs
One of the client-side detection measures that Cloudflare employs is the Turnstile CAPTCHA. It's a non-interactive challenge that runs under the hood to detect bots by analyzing signals such as browser environment, operating system, mouse movements, clicks, and more.

Whether or not Cloudflare displays the Turnstile CAPTCHA depends on a few factors, such as:

Site configuration: A website administrator may choose to enable the Turnstile challenge every time, occasionally, or never at all.
Risk level: Cloudflare may serve a Turnstile CAPTCHA only if the traffic is suspicious. For example, you may get the Turnstile challenge while using a programmed HTTP client and not get it if using a standard web browser like Google Chrome. For web scrapers, finding a Cloudflare Turnstile bypass solution is essential to avoiding interruptions.
Here's a sample Turnstile CAPTCHA on a Cloudflare-protected website:

scrapingcourse cloudflare blocked screenshot
Click to open the image in full screen
Scrape any website without getting blocked.
ZenRows bypasses Cloudflare, DataDome, and all other anti-bots for you.
Try for Free
Canvas Fingerprinting
Canvas fingerprinting allows a system to identify a web client's device class. A device class refers to the combination of browser, operating system, and graphics hardware used to access a webpage.

Canvas is an HTML5 API for drawing graphics and animations on a web page using JavaScript. A webpage queries your browser's canvas API to construct a canvas fingerprint and render an image. That image is then hashed to produce a fingerprint.

While canvas fingerprinting may not contain enough information to identify unique users, it helps the server to identify the differences between device classes. A canvas fingerprint depends on multiple layers of the computing system, such as:

Hardware: The graphics processing unit (GPU).
Low-level software: GPU driver, operating system (fonts, anti-aliasing/sub-pixel rendering algorithms).
High-level software: Web browser (image processing engine).
A variation in any of these layers produces a unique fingerprint, helping Cloudflare accurately differentiate between device classes.

Cloudflare maintains a large dataset of legitimate canvas fingerprints plus User Agent pairs. It then uses machine learning to identify mismatches between your canvas fingerprint and the expected one.

The specific canvas fingerprinting method used by Cloudflare is called Google's Picasso Fingerprinting. If you'd like to see canvas fingerprinting in action, check out Browserleak's live demo.

Event Tracking
Cloudflare adds event listeners to web pages. They keep track of user actions, such as mouse movements, clicks, or key presses. Most of the time, a real user will need to use their mouse or keyboard to browse. If Cloudflare detects a lack of consistent mouse or keyboard usage, it flags the user as a bot.

Environment API Querying
A browser has hundreds of Web APIs that can be used for bot detection. We can split them up into four general categories:

Browser-specific APIs: These specifications may exist in one browser and not the other. For example, window.chrome is a property that only exists in a Chrome browser. If your request indicates that you're using a Chrome browser but you send a Firefox User Agent, Cloudflare will flag it as a bot and block it.
Timestamp APIs: Cloudflare uses timestamp APIs, such as Date.now() or window.performance.timing.navigationStart, to track a user's speed metrics. The Bot Manager will block your request if these timestamps aren't legitimate. For example, browsing quickly or a mismatched navigationStart timestamp can tell Cloudflare you're a bot.
Automated browser detection: Cloudflare queries the browser for automated web browser properties. For example, the window.document.__selenium_unwrapped or window.callPhantom property indicates the usage of Selenium or PhantomJS, respectively. The presence of these properties in your scraper can get you blocked.
Sandboxing detection: Sandboxing refers to an attempt to emulate a browser in a non-browser environment. Cloudflare implements checks to prevent solving its challenges with emulated browser environments, such as JSDOM in NodeJS. For example, the detection script may look for the process object, which only exists in NodeJS. It can also detect if functions have been modified by using Function.prototype.toString.call(functionName) on the suspected function.
Now that you know Cloudflare's detection methods let's see how to bypass them.

Method #1: Use Cloudflare Solvers
Dedicated Cloudflare solvers are mostly useful when dealing with basic Cloudflare protections, and you want the solution to be within your control. There are several Cloudflare-solving tools and libraries out there. We've written guides on some well-known ones:

Cfscrape: A Python module for solving CAPTCHAs during scraping.
Cloudscraper: A web scraping library built to extract data from Cloudflare-protected pages.
FlareSolverr: A reverse proxy for accessing Cloudflare-protected websites.
Some of these tools, like Cloudscraper, have open-source and paid versions. Unfortunately, even their paid tiers often fail to keep up with Cloudflare's evolving ecosystem, which is becoming increasingly sophisticated to bypass. For instance, Cfscrape hasn't received any update for years.

Most Cloudflare solvers opt for static bypass, while others employ headless browsers to add a human touch to your scraper. For instance, Flaresolverr uses Selenium with the undetected-chromedriver to mimic a regular user. However, browsers consume significant resources, and running multiple instances can be challenging at scale.

Method #2: Web Scraping API to Bypass Cloudflare
Although all the techniques mentioned in this article may help, they can't guarantee success all the time. That's because Cloudflare frequently updates its security measures.

The easiest way to deal with Cloudflare is to use a web scraping API, such as ZenRows' Universal Scraper API. ZenRows provides all the toolkits required to scrape any website on a large scale without getting blocked. It uses cutting-edge technology to bypass all of Cloudflare's detection methods under the hood, so you can focus on your scraping logic rather than figuring out how to avoid anti-bot measures.

ZenRows is also compatible with all programming languages. All you need is a single API call to have ZenRows bypass Cloudflare protection and obtain your desired data.

To see how ZenRows works, let's use it to access the Cloudflare Challenge page, a website heavily protected by Cloudflare.

Sign up to load the ZenRows Request Builder. Paste the target URL in the link box, activate Premium Proxies, and set the Boost mode to JS Rendering.

building a scraper with zenrows
Click to open the image in full screen
Select your preferred language and choose the API connection mode. Click "Try it" to run the code inside the builder. You can also copy and paste the generated code into your scraper file to run it locally.

Here's the generated code for Python:

Example
# pip3 install requests
import requests

url = 'https://www.scrapingcourse.com/cloudflare-challenge'
apikey = '<YOUR _ZENROWS_API_KEY>'
params = {
    'url': url,
    'apikey': apikey,
    'js_render': 'true',
    'premium_proxy': 'true',
}
response = requests.get('https://api.zenrows.com/v1/', params=params)
print(response.text)
The above code outputs the target website's full-page HTML, proving you've bypassed Cloudflare:

Output
<html lang="en">
<head>
    <!-- ... -->
    <title>Cloudflare Challenge - ScrapingCourse.com</title>
    <!-- ... -->
</head>
<body>
    <!-- ... -->
    <h2>
        You bypassed the Cloudflare challenge! :D
    </h2>
    <!-- other content omitted for brevity -->
</body>
</html>
Your scraper now bypasses Cloudflare effectively!

Still, let's explore more options.

Method #3: Bypass Cloudflare CDN by Calling the Origin Server
Cloudflare can only block requests that pass through its network, so you can try sending a request directly to the origin server.

The process starts by finding the IP address of the server hosting the content. Once you have the origin IP, you can send your request directly to it without facing Cloudflare.

However, keep in mind that the process may not always work because locating the origin server's IP address is often challenging. Even when found, your HTTP client may not satisfy the origin server's configurations, resulting in active rejection of your request.

You can achieve this in two steps:

Find the Origin IP Address
Websites protected by Cloudflare typically have their DNS records hidden, but they may only partially hide them. Services such as mailings, databases, or subdomains may still point directly to the origin server. Looking up these services can reveal the website's origin server IP address.

Several solutions can give valuable information about a website's services and subdomains. For example, databases like Shodan and Censys or tools like CloudFlair and CloudPeler may reveal internal details.

Once you obtain the origin IP address from internal services, the next step is communicating directly with it behind Cloudflare's protection.

Request Data From the Origin Server
So, you got the original IP address. That's great! But what do you do with it?

You can try to paste it into the URL bar on your browser, but that may fail because the request lacks a valid Host header. Besides, multiple hosts might be sharing that IP address through virtual hosting, making it difficult for the server to determine which website you are trying to access.

Tools like cURL can allow you to specify a host header while requesting the origin server's IP address. This method can force the target domain to route directly through the origin server instead of Cloudflare's DNS. However, this method often fails because many origin servers only accept traffic from trusted IPs.

Another option is to force your computer's host file (e.g., /etc/hosts) to map a specific domain name to an IP address manually and avoid checking the DNS. However, this is unscalable because host file configuration across multiple machines is time-consuming.

Method #4: Implement Fortified Headless Browsers
Headless browsers, including Selenium, Playwright, and Puppeteer, allow you to interact with web pages as a human.

However, since headless browsers are designed for automation testing and not for scraping, they have several traits that make them easily identifiable by Cloudflare.

For example, Selenium and Puppeteer expose bot-like attributes like navigator.webdriver, which may cause Cloudflare to flag and block you. Let's test a basic Selenium scraper on CreepJS, a website that returns your browser fingerprints, to see how detectable it is:

Example
# import the required libraries
from selenium import webdriver
import time

# set up the WebDriver for Chrome
options = webdriver.ChromeOptions()

# initialize the Chrome WebDriver
driver = webdriver.Chrome(options=options)

# open the specified URL
driver.get('https://abrahamjuliot.github.io/creepjs/')

# wait for 60 seconds
time.sleep(60)

# close the browser
driver.quit()
Once the scraper opens the test website in the automated Chrome browser, scroll down to the Headless section. The 33% headless flag indicates that the requesting client is likely a headless browser.

creepjs fingerprint test headless flag
Click to open the image in full screen
Click the hashed link on the right of the 33% headless flag. You'll see that the webDriverIsOn property is true. This information further signals Cloudflare that the request originates from an automated bot:

Example
webDriverIsOn: true
hasHeadlessUA: false
hasHeadlessWorkerUA: false
But no worries. There are anti-bot bypass solutions for each of the most popular headless browsers:

Selenium: Undetected_chromedriver gets the base Selenium ready to bypass Cloudflare by optimizing and patching it.
Puppeteer: The Stealth plugin is a handy bypass tool when scraping with Puppeteer. And the Puppeteer extra library comes with other valuable plugins like Adblocker.
Playwright: The Stealth plugin mentioned above is also available for Playwright.
Most of these solutions can patch browser fingerprints to mimic a real browser. For example, you can use Puppeteer's Stealth plugin or the undetected_chromedriver to remove the WebDriver property from your scraper.

Let's rerun the previous fingerprinting test with the undetected_chromedriver in Selenium to see how that works:

Example
# import the required libraries
import undetected_chromedriver as uc
import time
 
# define Chrome options
options = uc.ChromeOptions()

# set headless to False to run in non-headless mode
options.headless = False

# set up the WebDriver for Chrome
driver = uc.Chrome(use_subprocess=True, options=options)

# open the specified URL
driver.get('https://abrahamjuliot.github.io/creepjs/')

# wait for 60 seconds
time.sleep(60)

# close the browser
driver.close()
The result now shows 0% headless. This means the server now sees your Selenium scraper as a real browser.

reepjs fingerprint test without headless flag
Click to open the image in full screen
To confirm this result, click the hashed link to the right of the headless flag as you did earlier. The webDriverIsOn property now returns false. This result shows that the undetected_chromedriver has patched the WebDriver in Selenium's ChromeDriver:

Example
webDriverIsOn: false
hasHeadlessUA: false
hasHeadlessWorkerUA: false
With the above modification, anti-bots are less likely to flag you as a bot.

However, these headless browsers have a few significant downsides, such as memory and resource overuse.

While using headless browsers, you can block resources like images to improve load time.

Still, keep in mind that anti-bots like Cloudflare load certain assets such as images, JavaScript, and stylesheets to perform their checks. So, the security system may deny you access to a protected site due to aggressive resource blocking.

If you want to learn the in-depth details of how to add stealth plugins to headless browsers, check the following tutorials:

Puppeteer Stealth for Puppeteer.
Playwright Stealth for Playwright.
Selenium Stealth for Selenium.
Method #5: Smart Proxies to Get Past Cloudflare
A proxy routes your request through a different IP, making it appear to originate from another machine. If your scraper gets blocked by Cloudflare site-protection, using proxies can help you avoid detection.

You can use free or premium smart proxies. However, free proxies are short-lived, making them unreliable in real-world projects.

That’s why it’s better to use premium web scraping proxies. They rotate IPs from a pool of network providers' IP addresses, allowing you to mimic different users through multiple requests. Smart proxies are also easy to maintain since IP rotation is automated.

The smart proxy that guarantees success is the ZenRows proxy rotator. It provides auto-rotating residential proxies at a competitive price. The tool also gives you access to other anti-bot bypass solutions.

Method #6: Bypass Cloudflare Waiting Room and Reverse-engineer Its Challenge
Checking if the site connection is secure

Checking your browser before accessing XXXXXXXX.com

If you see these messages, it means you couldn't bypass the Cloudflare waiting room and ran into this:

G2 human verification page
Click to open the image in full screen
Also known as the Cloudflare JavaScript challenge or the Cloudflare I Am Under Attack page, this is Cloudflare's principal protection. To bypass Cloudflare bot protection, you need to skip the Cloudflare waiting room.

What Is Cloudflare Waiting Room?
f you've been looking for how to bypass Cloudflare human check, understanding this waiting period is crucial to accessing protected content. When you visit a Cloudflare-protected site in your browser, you must first wait a few seconds in the Cloudflare waiting room. During that time, your browser solves challenges to prove you're not a robot. If you're labeled as a bot, you'll be given an "Access Denied" error, making a Cloudflare waiting room bypass essential for uninterrupted access. Otherwise, you'll be automatically redirected to the web page.

How Long Does It Take to Bypass Cloudflare Waiting Room?
You'll be placed in the waiting room for a few seconds. The exact time depends on the target's security level and how your scraper handles the tests. For highly protected sites, this process could take up to ten seconds.

Once the challenge is solved, you can browse the site.

How Do I Bypass Cloudflare's Waiting Room?
Ideally, you can bypass Cloudflare's waiting room by solving the JavaScript challenges and proving you're human.

Another approach is analyzing Cloudflare's JavaScript challenge to understand the algorithm responsible for generating the challenge and validating the response. This way, you can reverse-engineer the script.

What Is the Purpose of Bypassing Cloudflare's Waiting Room?
The purpose of bypassing the Cloudflare waiting room is to gain access to onsite data. Every request to a Cloudflare-protected URL encounters the waiting room, where it undergoes challenges in order to get redirected to the actual website. Your web scraper has to go through the same process.

Reverse-engineering the Cloudflare JavaScript Challenge
For this example, we will reverse-engineer the Cloudflare waiting room page as it appears on G2. Feel free to click the link and follow along!

Step 1: Check out the network log
Open up the developer tools in your browser and navigate to the "Network" tab. Then, leave them open and browse the G2 site.

After you're redirected from the challenge page to the actual site, you'll notice the following crucial requests (in chronological order):

An initial GET to https://www.g2.com/, with the response body as the waiting room's HTML. The HTML contains <script> tags containing an important anonymous function. This function does some initialization and loads the "initial challenge" script.
Example
// The script from the waiting room HTML. 
(function () { 
	window._cf_chl_opt = { 
		cvId: '2', 
		cType: 'non-interactive', 
		cNounce: '12107', 
		cRay: '744da33dfa643ff2', 
		cHash: 'c9f67a0e7ada3f3', 
		/* ... */ 
	}; 
	var trkjs = document.createElement('img'); 
	/* ... */ 
	var cpo = document.createElement('script'); 
	cpo.src = '/cdn-cgi/challenge-platform/h/g/orchestrate/jsch/v1?ray=744da33dfa643ff2'; 
	window._cf_chl_opt.cOgUHash = /* ... */ 
	window._cf_chl_opt.cOgUQuery = /* ... */ 
	if (window.history && window.history.replaceState) { 
		/* ... */ 
	} 
	document.getElementsByTagName('head')[0].appendChild(cpo); 
})();
This script rotates per request, so it may look slightly different if you follow along in your browser.

A GET to the "initial challenge" script: https://www.g2.com/cdn-cgi/challenge-platform/h/g/orchestrate/jsch/v1?ray=<rayID>, where <rayId> is the value of window._cf_chl_opt.cRay from above. It returns an obfuscated JavaScript script, which you can view here. This script rotates changes on each request.
The GET request for the 'initial challenge' script
Click to open the image in full screen
A POST request to https://www.g2.com/cdn-cgi/challenge-platform/h/g/flow/ov1/<parsedStringFromJS>/<rayID>/<cHash>, where <parsedStringFromJS> is a string defined in the initial challenge script and <cHash> is the value of window._cf_chl_opt.cHash. The request body is a URL-encoded payload of the format: v_<rayID>=<initialChallengeSolution>. The response body to this request seems to be a long base64-encoded string.
The initial challenge request. Payload (Left), Response (Right)
Click to open the image in full screen
A second POST request to https://www.g2.com/cdn-cgi/challenge-platform/h/g/flow/ov1/<parsedStringFromJS>/<rayID>/<cHash>. The payload follows the same format as the previous request and, once again, returns a long base64-encoded string. This request is responsible for sending the solution to the second Cloudflare challenge.
The second challenge request. Payload (Left), Response (Right)
Click to open the image in full screen
A final POST request to https://www.g2.com/, with some crypto form data in this format:

Example
md: <string> 
r: <string> 
sh: <string> 
aw: <string> 
The response to this request gives us the actual HTML of the target webpage and a cf_clearance cookie that allows us to freely access the site without solving another challenge.

The final POST request. Payload (Left), Response Cookies (Right)
Click to open the image in full screen
The request flow doesn't give us too much information, especially since all the data looks to be either encrypted or a random text stream. So, that rules out trying to black-box reverse engineer our way to a Cloudflare bypass.

This might leave you with even more questions than you started with. Where do these requests come from? What does the data in the payloads represent? What's the purpose of the base64 response bodies?

There's no better place to search for answers than the "initial challenge" script. Be warned, this is no walk in the park! If you're ready for the challenge, stick with us. We'll start with some dynamic analysis.

Step 2: Debug the Cloudflare Javascript challenge script
Cloudflare's scripts are heavily obfuscated. It would be a nightmare to read the script as-is without any knowledge of its functionality.

Fortunately for us, at the time of writing this, Cloudflare doesn't use any kind of anti-debugging protection. Open up your browser's developer tools and set up an XHR/fetch breakpoint for all requests:

Setting an xtr breakpoint
Click to open the image in full screen
Be sure to clear your cookies so that Cloudflare will place you in the waiting room again. Keeping your developer tools open, navigate to G2.

You'll notice that within a few milliseconds after the "initial challenge" script loads, your XHR breakpoint gets triggered (before the first POST request is sent).

1st Triggered XHR Breakpoint
Click to open the image in full screen
Now, you can see and access all the variables and functions in the current scope. However, you can deduce little from the variable values shown on-screen, and the code is unreadable.

Looking closely at the script, you'll notice that one function is called over a thousand times. In this example, that's the c function (though it might have a different name in your script). When called, there is always a single stringified hex number as the argument. Let's try running it in the DevTools console:

Running the c function in the console
Click to open the image in full screen
Wow! It appears that Cloudflare uses a string-concealing obfuscation mechanism. By running the function and replacing its calls with its return values, we can simplify the bottom two lines in the above screenshot to this:

Example
// The simplified code 
(aG = aw["Cowze"](JSON["stringify"](o["_cf_chl_ctx"]))["replace"]("+", "%2b")), 
aE["send"](aB.FptpP(aB.RfgQh("v_" + o["_cf_chl_opt"]["cRay"], "="), aG));
Using the same technique of running code in the console, we can deduce that the variables o and aE represent window and an XMLHttpRequest instance, respectively. We can also convert bracket notation to dot notation to yield:

Example
// The above code, even more simplified! 
(aG = aw.Cowze(JSON.stringify(window._cf_chl_ctx)).replace("+", "%2b")), 
	// aE = new XMLHttpRequest(), an XMLHttpRequest instance initialized earlier in the script 
	aE.send(aB.FptpP(aB.RfgQh("v_" + window._cf_chl_opt.cRay, "="), aG));
It's not perfect, but the code is getting much easier to read. Simplifying all the string-concealing function calls would improve the script's readability. However, doing it manually would take an eternity. We'll tackle this challenge in the next section, but let's move on for now.

If you press the "continue until next breakpoint" button in your debugger, your browser will send the first post request. It will pause on the next breakpoint immediately after receiving a response:

2nd Triggered XHR Breakpoint
Click to open the image in full screen
The debugger is paused in a completely different script. This new script is what we'll call Cloudflare's "main" or "second" Javascript challenge. But if you look at the network log, there was no GET request to this specific script! So, where did it come from?

Taking a closer look at the script, we can see that it's an anonymous function. The script name, in our case, is VM279. According to a thread on StackOverflow, this second script is likely being evaluated within the initial challenge script, using eval or similar. We can confirm this because the call stack shows the Cloudflare "initial challenge" script as the initiator (See: green boxes in the screenshot).

If we click on the initiator, we can see where this script is being evaluated in the "initial challenge" script:

Location of the initiator
Click to open the image in full screen
We'll use the same method of evaluating the c function calls to undo the string concealing and replacing o with window, which gives us this:

Example
// The line of code that initiates the second JavaScript challenge 
 
// Note: aE = new XMLHttpRequest(), an XMLHttpRequest instance initialized earlier in the script 
new window.Function(aB.pgNsC(ax, aE.responseText))();
It looks like this function is creating a new function based on the data contained in the responseText of the XMLHttpRequest from the previous breakpoint. Cloudflare probably uses some cipher to decrypt it into an executable script.

We've made some progress, but the Cloudflare scripts remain unreadable. Even with manual debugging, we won't be able to figure out much more. If you want to create a Cloudflare bypass, we must understand it fully. And to do that, we need to deobfuscate it.

Step 3: Deobfuscate the Cloudflare Javascript challenge script
This is going to take a lot of work. Cloudflare uses many obfuscation techniques in its code, and it wouldn't be practical to cover them all in this article. Here's a (non-exhaustive) list of examples:

String Concealing: Cloudflare removes all references to string literals. In the previous section, we saw that the c function acted as a string concealer.
Control Flow Flattening: Cloudflare obscures the control flow of a program by emulating assembly-like JUMP instructions by using an infinite loop and a central switch statement dispatcher. Here's an example from the Cloudflare script:
Example
// An example of control flow flattening from the Cloudflare script. 
function Y(ay, aD, aC, aB, aA, az) { 
	// The aB array holds a list of all the instructions. 
	aB = "1|6|11|0|15|9|3|10"["split"]("|"); 
 
	// This is the infinite loop 
	for (aC = 0; true; ) { 
		// The below switch statement is the "dispatcher" 
		// The value of the aB[aC] acts as an instruction pointer, determining which switch case to execute. 
		// After each switch statement finishes executing, the instruction pointer is incremented by one to retrieve the next instruction. 
 
		switch (aB[aC++]) { 
			case "0": 
				/* ... */ 
				continue; 
 
			case "1": 
				/* ... */ 
				continue; 
 
			case "3": 
				/* ... */ 
				continue; 
 
			case "6": 
				/* ... */ 
				continue; 
 
			case "9": 
				/* ... */ 
				continue; 
 
			case "10": 
				// Exit the function. This is the final switch case 
				return aD; 
 
			case "11": 
				/* ... */ 
				continue; 
 
			case "15": 
				/* ... */ 
				continue; 
		} 
 
		break; 
	} 
}
Proxy Functions: Cloudflare replaces all binary operations (+,-,==, /, etc.) with function calls. This decreases code readability, as you constantly need to look up the definition of the extra functions. Here's an example:
Example
// An example of proxy function usage 
 
az = {}; 
 
// '+' operation proxy function 
az.pNrrD = function (aB, aC) { 
	return aB + aC; 
}; 
// '-' operation proxy function 
az.aZawd = function (aB, aC) { 
	return aB - aC; 
}; 
// '===' operation proxy function 
az.fhjsC = function (aB, aC) { 
	return aB === aC; 
}; 
 
/* ... */ 
 
// Equivalent to ((1 + 3) - 4) === 0 
Atomic Operations: Especially in the main/second challenge script, Cloudflare converts simple strings or numeric literals into long, convoluted expressions, taking advantage of the atomic parts of JavaScript (unary expression, math operations, and empty arrays). This technique is very reminiscent of JSFuck. Example:
Example
// Believe it or not, this is equivalent to: 
// a = 1.156310815361637 
a = 
	(!+[] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		[] + 
		(!+[] + !![] + !![] + !![]) + 
		-~~~[] + 
		(!+-[] + +-!![] + -[]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![] + !![] + !![]) + 
		-~~~[]) / 
	+( 
		!+[] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		!![] + 
		[] + 
		-~~~[] + 
		(!+[] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![] + !![] + !![] + !![]) + 
		(!+[] + !![] + !![]) 
	);
What makes bypassing Cloudflare bypass hard is the script's obfuscation and dynamic nature. Each time you enter a Cloudflare waiting room, you'll face new challenge scripts.

If you want to create your own Cloudflare bypass, you'll need some highly specialized skills. The obfuscation of Cloudflare's challenge scripts is good enough that you can't just throw it in a general-purpose deobfuscator and get a readable output. You'll need to create a custom deobfuscator capable of dynamically parsing and transforming each new Cloudflare challenge script into human-readable code. (Hint: Try manipulating the script's abstract syntax tree.)

Once you've made a working dynamic deobfuscator, you'll be able to better understand all the checks Cloudflare's anti-bot performs on your browser and how to replicate the challenge-solving process.

In the next step, we'll analyze some active bot detection implementations from the deobfuscated Cloudflare script. Let's get to it!

Step 4: Analyze the deobfuscated script
Remember those cryptic payloads and base64 encoded response bodies? Now we can understand how they work!

Cloudflare's encryption

Recall the code snippet in which we determined that the response text was being used to evaluate the main/second challenge script:

Example
// Note: aE = new XMLHttpRequest(), an XMLHttpRequest instance initialized earlier in the script 
new window.Function(aB.pgNsC(ax, aE.responseText))();
The deobfuscated version looks like this:

Example
In the end, `ab.pgNsC` was just a proxy wrapper for the `ax` function. The deobfuscated `ax` function looks like this:
Example
ax = function (ay) { 
	var aF; 
	var aE = window._cf_chl_opt.cRay + "_" + 0; 
	aE = aE.replace(/./g, function (_, aH) { 
		32 ^= aE.charCodeAt(aH); 
	}); 
	ay = window.atob(ay); 
	var aD = []; 
	for ( 
		var aB = -1; 
		!isNaN((aF = ay.charCodeAt(++aB))); 
		aD.push(String.fromCharCode(((aF & 255) - 32 - (aB % 65535) + 65535) % 255)) 
	) {} 
	return aD.join(""); 
};
Can you guess what this function does? It's a decryption function!

Cloudflare encrypts the main/second challenge script with a cipher. Then, after the first POST request to solve the initial challenge, Cloudflare returns the encrypted second challenge script.

To actually execute the challenge, it's decrypted into a string with the ax function using window._cf_chl_opt.cRay as the decryption key. That string is then passed into the Function constructor to create a new function and executed with ()!

We also previously discussed Cloudflare's active bot detection techniques. Now, we can revisit a few of them to see their implementations!

CAPTCHAs

Here, we can see how Cloudflare loads a Turnstile instance:

Example
(function() {
/*...*/
 
    function lt(e, a, r, o, c, u, g) {
        var b = "https://challenges.cloudflare.com";
        if (c) b = e["base-url"] || b;
        var l = u ? "h/" + u + "/" : "", h = g ? "?" + g : "";
        return `${b}/cdn-cgi/challenge-platform/${l}turnstile/if/ov2/av0/rcv${o}/${e}/${a}/${r.theme}/${r.size}${h}`;
    }
/*...*/
 
    var y = {
        turnstileLoadInitTimeMs: D(),
        scriptWasLoadedAsync: false,
        isReady: false,
        widgetMap: new Map()
    };
/*...*/
 
    var I = Kt(), z = I.params.get("onload");
    if (z) setTimeout(() => typeof window[z] === "function" ? window[z]() : x(`Unable to find onload callback '${z}'`), 0);
 
    window.turnstile = { ready: n => { if (typeof n !== "function") p('Expected a function', 3841); n(); y.isReady && n(); _t.push(n); }, execute: /*...*/, render: /*...*/, reset: /*...*/, remove: /*...*/, getResponse: /*...*/, isExpired: /*...*/ };
/*...*/
 
    window.addEventListener("message", R);
    document.readyState === "complete" || document.readyState === "interactive" ? setTimeout(ar, 0) : window.addEventListener("DOMContentLoaded", ar);
/*...*/
})();
Canvas fingerprinting

In this snippet, Cloudflare is creating an array of canvas fingerprinting functions for use later on in the script:

Example
S = [ 
	/* ... */ 
	function (a3, a4, a5, af, ae, ad, ac, ab, aa, a9, a8, a7, a6) { 
		a3.shadowBlur = 1 + O(L); 
		a3.shadowColor = R[O(R.length)]; 
		a3.beginPath(); 
		ad = a4.width / H; 
		ae = a4.height / H; 
		a8 = ad * a5 + O(ad); 
		a9 = O(ae); 
		a3.moveTo(a8 | 0, a9 | 0); 
		af = a4.width / 2 + O(a4.width); 
		aa = O(a4.height / 2); 
		ac = a4.width - a8; 
		ab = a4.height - a9; 
		a3.quadraticCurveTo(af | 0, aa | 0, ac | 0, ab | 0); 
		a3.stroke(); 
		return true; 
	}, 
	/* ... */ 
];
Timestamp tracking

There are many places in the script where Cloudflare queries the browser for timestamps. Here's an example:

Example
k = new Array(); 
pt = -1; 
 
/* ... */ 
if (window.performance.timing && window.performance.timing.navigationStart) { 
	ns = window.performance.timing.navigationStart; 
} 
for (var j = 0; j < 10; j++) { 
	k.push(Date.now() - ns - pt); 
}
Event tracking

Here, we can see that Cloudflare adds EventListeners to the webpage to track mouse movements, mouse clicks, and key presses.

Example
function x(aE, aD, aC, aA, az, ay) { 
	aA = false; 
	aE = function (aF, aG, aH) { 
		p.addEventListener 
			? p.addEventListener(aF, aG, aH) 
			: p.attachEvent("on" + aF, aG); 
	}; 
	aE("keydown", aB, aD); 
	aE("pointermove", aB, aD); 
	aE("pointerover", aB, aD); 
	aE("touchstart", aB, aD); 
	aE("mousemove", aB, aD); 
	aE("click", aB, aD); 
	function aB() { 
		/* .. */ 
	} 
}
Automated browser detection

Here are a few of the checks Cloudflare has to detect the use of popular automated browsing libraries:

Example
function _0x15ee4f(_0x4daef8) { 
	return { 
		/* .. */ 
		wb: !(!_0x4daef8.navigator || !_0x4daef8.navigator.webdriver), 
		wp: !(!_0x4daef8.callPhantom && !_0x4daef8._phantom), 
		wn: !!_0x4daef8.__nightmare, 
		ch: !!_0x4daef8.chrome, 
		ws: !!( 
			_0x4daef8.document.__selenium_unwrapped || 
			_0x4daef8.document.__webdriver_evaluate || 
			_0x4daef8.document.__driver_evaluate 
		), 
		wd: !(!_0x4daef8.domAutomation && !_0x4daef8.domAutomationController), 
	}; 
}
Sandboxing detection

In this snippet, the script checks if it's running in a NodeJS environment by searching for the node-only process object:

Example
(function () { 
	SGPnwmT[SGPnwmT[0]] -= +( 
		(Object.prototype.toString.call( 
			typeof globalThis.process !== "undefined" ? globalThis.process : 0 
		) === 
			"[object process]") === 
		false 
	); 
	/* ... */ 
});
To detect any modification of native functions (e.g., monkey patching, Cloudflare executes toString on them to check if they return the "[native code]" or not.

Example
c = function (g, h) { 
	return ( 
		h instanceof g.Function && 
		g.Function.prototype.toString.call(h).indexOf("[native code]") > 0 
	); 
};
Step 5: Put it all together

Phew, it's been quite the journey so far! That was a lot to take in. Let's reflect on what you've learned so far:

The purpose of Cloudflare's anti-bot.
The active and passive bot detection techniques Cloudflare uses.
What is the Cloudflare waiting room/challenge page.
How to reverse engineer the Cloudflare waiting room's request flow.
How to deobfuscate the Cloudflare challenge scripts.
How Cloudflare implements bot detection techniques in their Javascript challenge.
Put it all together, and give bypassing Cloudflare a go!

Method #7: Cloudflare CAPTCHA Bypass
The Cloudflare Turnstile CAPTCHAs are a challenge to web scrapers. Most of the ones you'll encounter during scraping have the highest security level.

cloudflare turnstile sample
Click to open the image in full screen
The sites with the highest Cloudflare security level will show the CAPTCHA challenge even to regular users using real browsers.

The solution might be building a Cloudflare CAPTCHA bypass using a solver service like 2Captcha. These services send the CAPTCHA to real human solvers and return the solution, and you can continue with that.

Those solver services are slow and relatively expensive at scale, but they can be used as a plan B for cases where all the other methods fail.

Try to analyze and understand your target website. For example, some sites only use the maximum security level at certain hours or days of the week. If you can identify these periods and skip the protection, you won't need to add the extra effort of CAPTCHA solvers. Additionally, we'd suggest applying some (or all) of the methods explained.

That said, the best way to bypass CAPTCHA during scraping is to integrate a complete solution like ZenRows. It solves and bypasses the Cloudflare Turnstile CAPTCHA and all other CAPTCHAs, allowing you to scrape any website without getting blocked.

Method #8: Scrape Google Cache
Although Google no longer supports access to cached pages, sites such as WebCite and Internet Archive have old copies of many websites. They let you access a snapshot of a protected website without visiting the website's domain or passing through Cloudflare's CDN.

This method's shortcoming is that the data might be outdated, preventing you from getting your desired content.

So, ask yourself the following questions before using these archives:

Is the data you need present there and updated?
Is the security level of these archives lower than your original target?
If the answer to both is true and none of the previous methods worked for you, try this option. Start by manually searching your target website on any of these archives to see if it has a cached version.

For instance, to use Internet Archive, paste your target URL in the search box and hit Enter. If a snapshot is available, you'll get several calendar options of cached versions of the target site. Select a date and time to access the website's snapshot.

archived version of g2 reviews page
Click to open the image in full screen
Once you get the cached version, you can copy the Internet Archive snapshot URL from your address bar and request it directly via your scraper.

Method #9: DIY Cloudflare Bypass
We've highlighted several ways to handle Cloudflare. You can combine many methods for the best result.

As you now know, Cloudflare has two types of bot detection methods: passive fingerprinting and active bot detection (through JavaScript challenge). You'll have to sneak under the radar of both to bypass Cloudflare. Here are some tips for each.

Bypassing Cloudflare's Passive Bot Detection
Use high-quality proxies: To disguise your scraper as a legitimate user, use residential proxies. Cloudflare easily detects datacenter proxies and VPNs and flags them as suspicious traffic. Many requests from a single IP address can also lead to blocks, so ensure to rotate your proxies per session to avoid that. If you're still facing blocks, a specialized Cloudflare CAPTCHA proxy will help you bypass them and skip the waiting room.
Mimic your browser's headers: Make your scraper's requests look as legitimate as possible by ensuring you send all the HTTP headers a real browser would send. That includes having valid cookie headers for each request!
Match an allowed fingerprint: If you've opted for the browser automation route, your scraper might fulfill this requirement by default. However, this only works if you use the exact User Agent and browser version the automation tool is built upon. This process becomes more tedious when developing a full request-based scraper because you'll need to capture and analyze packets from the browsers you intend to impersonate. Your chosen programming language must also have enough low-level access to control all the components of Cloudflare's TLS and HTTP/2 fingerprinting specifications to match those of a real browser.
Remember, passive bot detection is Cloudflare's first layer of defense. You'll be blocked immediately if your activity is labeled suspicious by the passive anti-bot system. However, slipping past them may allow you to skip over the active bot protection checks.

Bypassing Cloudflare's Active Bot Detection
Reconstruct the challenge-solving logic: This technique requires an expert understanding of the Cloudflare waiting room's internals. Study its request flow and deobfuscated JavaScript. You'll need to figure out what checks Cloudflare performs, their execution order, and how you can bypass Cloudflare security check mechanisms. You'll also need to replicate the encryption and decryption of various Cloudflare payloads. This step is the most difficult because the Cloudflare challenge scripts are dynamic. Every session might even require you to deobfuscate a new script on the fly to parse specific values to your solver.
Collect real device data: Even if you understand the fingerprints' internal structure, impersonating some of them is impractical. For example, unlike a TLS or HTTP/2 fingerprint, Cloudflare's Canvas fingerprinting relies heavily on moving parts from software and hardware. The functionality of hardware components is advanced, so imitating them is almost impossible. Even if you get close to patching them, you'll waste valuable development time. Instead, consider collecting fingerprint data from real users' devices. Then, you can inject this data into your solver whenever you need to use it. But if you collect too few fingerprints, you may get blocked. Your best option is to host a collector on a high-traffic webpage to ensure you have enough devices.
Use automated browsers/sandbox the script. If you want to abstract some challenge-solving logic, consider executing the Cloudflare JavaScript challenges directly. You can achieve this within the browser by using automated tools or emulating the browser in a sandbox such as JSDOM. The downside to this approach is the reduced performance. Running or emulating a browser environment will be much slower and computationally expensive than a request/algorithm-based challenge solver. Also, remember that Cloudflare checks for automated browsers and sandboxing. You must first understand which detection mechanisms exist and how they work to bypass them. So, whether sandboxed or not, you won't be able to skip deobfuscating the Cloudflare challenge scripts! You can achieve a headless browser Cloudflare bypass, but it will take extra effort.
Great job if you've gotten this far! You're now familiar with how to bypass Cloudflare's anti-bot challenge.

Don't fret if you feel lost during the process. Bypassing Cloudflare or any other anti-bot can feel daunting, but that doesn't mean you should give up on your scraping project! With the variety of methods available, you're bound to find one that works for your use case.

Conclusion
You've learned about Cloudflare's bot detection techniques and how to reverse engineer them. As mentioned, none of the techniques is one-size-fits-all. Combining a couple of custom methods can be more effective.

That said, the methods you learned today aren't Cloudflare-specific. You can also apply them to bypass other anti-bots such as Akamai and DataDome. If you'd like to learn more about it, read the following guides:

How to bypass DataDome.
How to bypass Akamai.
However, bypassing Cloudflare yourself is often tedious and resource-intensive. Therefore, the most reliable and efficient way to bypass Cloudflare protection is to use a web scraping API like ZenRows.

Frequent Questions
1. Is It Possible to Bypass Cloudflare?
Yes, it's possible to bypass Cloudflare protection. Its anti-bot techniques can be classified into two, namely, passive fingerprinting and active anti-bot detection. So, to bypass Cloudflare, you must find your way around them.

2. Why Is My IP Blocked by Cloudflare?
Cloudflare may block your IP address if you exhibit bot-like behavior, such as quickly making too many requests, using non-browser user agents, etc. Another reason could be that your IP has been blocklisted due to association with suspicious activity.

3. How to get unblocked from Cloudflare?
Getting around Cloudflare's blocks requires a strategic approach to bypass its robust anti-bot measures. Here are some of the most effective methods:

Use Smart Proxies: Cloudflare often blocks requests from datacenter IPs or known VPNs. Residential proxies or rotating proxies can help disguise your scraper as legitimate traffic.
Mimic Browser Behavior: Use headless browsers like Puppeteer, Playwright, or Selenium with stealth plugins to replicate human-like browsing patterns. This includes mimicking mouse movements, clicks, and proper header configurations.
Leverage Web Scraping APIs: Tools like ZenRows are specifically designed to bypass Cloudflare effortlessly by handling all the anti-bot challenges for you.
Solve Cloudflare Challenges: Reverse-engineer Cloudflare's JavaScript challenges or CAPTCHAs using libraries like FlareSolverr or CAPTCHA-solving services such as 2Captcha.
Remember, bypassing Cloudflare is a cat-and-mouse game, so staying updated with its latest detection methods is key.

4. How to bypass Cloudflare human check?
Bypassing Cloudflare’s human check requires strategies to mimic legitimate user behavior. Here are the most effective methods:

Use ZenRows: ZenRows's Universal Scraper API automatically bypasses Cloudflare’s human checks, including JavaScript challenges and CAPTCHAs, making scraping seamless and hassle-free.
Stealth Browsers: Tools like Puppeteer or Playwright with stealth plugins replicate human interactions, such as mouse movements and keyboard inputs.
CAPTCHA Solvers: Services like 2Captcha or Anti-Captcha handle Turnstile challenges, though they can be slow and costly.
Reverse-Engineer Challenges: Decrypt and solve Cloudflare’s JavaScript challenges to send validated responses, though this is highly technical.
ZenRows is the easiest and most reliable option, saving time and effort while ensuring uninterrupted access.