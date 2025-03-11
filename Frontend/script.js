// Define helper functions outside the event listener
async function get_feedback(apiEndpoint, url) {
    try {
        // Make the POST request to the Flask API
        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                "url": url
            }),
        });

        // Check if the response is ok (status code 200-299)
        if (!response.ok) {
            throw new Error('Error: cannot get feedback, please try later');
        }

        // Parse the JSON response
        const data = await response.json();
        console.log(data);

        // Extract scores and feedback from the response
        const score = data.score;
        const feedback = data.evaluation;
        console.log(score, feedback);

        return { score, feedback }; // Return an object
    } catch (error) {
        // Handle errors
        console.error('Error calling Flask API:', error);
        return { score: 1, feedback: "Error fetching feedback" };
    }
}

function updateChart(chartId, scoreId, score) {
    const chartElement = document.getElementById(chartId);
    const scoreElement = document.getElementById(scoreId);
    const maxScore = 5;
    const circumference = 283; // 2 * π * r (r = 45)
    const offset = circumference - (score / maxScore) * circumference;

    // Update the stroke dash offset
    chartElement.style.strokeDashoffset = offset;

    // Update the score text
    scoreElement.textContent = score.toFixed(1); // Display score with 1 decimal place

    // Update the stroke color based on the score
    if (score >= 4) {
        chartElement.style.stroke = '#4CAF50'; // Green
    } else if (score >= 3) {
        chartElement.style.stroke = '#FFEB3B'; // Yellow
    } else {
        chartElement.style.stroke = '#F44336'; // Red
    }
}

function updateFeedbackBox(boxId, feedback) {
    const feedbackBox = document.getElementById(boxId);
    if (feedbackBox) {
        feedbackBox.textContent = feedback.substring(0, 10000); // Limit feedback to 200 words
    }
}

// Add event listener for the load button
document.getElementById('loadButton').addEventListener('click', async function () {
    const url = document.getElementById('urlInput').value.trim();

    if (!url) {
        console.error('Please enter a valid URL');
        alert('Please enter a valid URL.');
        return;
    }

    try {
        // Load the website into the iframe
        document.getElementById('websiteFrame').src = url;
        const loadingOverlay = document.getElementById('loadingOverlay');
        loadingOverlay.style.display = 'flex';
        // Fetch feedback from all APIs concurrently
        const [userExperienceResponse, htmlResponse, securityResponse] = await Promise.all([
            get_feedback('http://127.0.0.1:5000/evaluate_user_experience', url),
            get_feedback('http://127.0.0.1:5000/evaluate_html', url),
            get_feedback('http://127.0.0.1:5000/evaluate_security', url),
        ]);
        loadingOverlay.style.display = 'none';
        // Destructure responses
        const { score: user_experience_score, feedback: user_experience_feedback } = userExperienceResponse;
        const { score: html_score, feedback: html_feedback } = htmlResponse;
        const { score: app_security_score, feedback: app_security_feedback } = securityResponse;

        // Log results
        console.log('User Experience Score:', user_experience_score);
        console.log('User Experience Feedback:', user_experience_feedback);
        updateChart('chart2', 'score2', user_experience_score); // Update User Experience chart
        updateFeedbackBox('user-experience-feedback', user_experience_feedback); // Update User Experience feedback box

        console.log('HTML Score:', html_score);
        console.log('HTML Feedback:', html_feedback);
        updateChart('chart1', 'score1', html_score); // Update HTML chart
        updateFeedbackBox('html-feedback', html_feedback); // Update HTML feedback box

        console.log('Security Score:', app_security_score);
        console.log('Security Feedback:', app_security_feedback);
        updateChart('chart3', 'score3', app_security_score); // Update Security chart
        updateFeedbackBox('app-security-feedback', app_security_feedback); // Update Security feedback box

    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while fetching feedback. Please try again.');
    }finally {
        // Hide the spinner
        
    }
});

// Add event listener for the capture button
document.getElementById('captureButton').addEventListener('click', async function () {
    const url = document.getElementById('urlInput').value.trim();

    if (!url) {
        console.error('Please enter a valid URL');
        alert('Please enter a valid URL.');
        return;
    }

    try {
        // Load the website into the iframe
        document.getElementById('websiteFrame').src = url;
        const screenshotResponse = await fetch('http://127.0.0.1:5000/take_screenshot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        });

        // Check if the screenshot response is ok (status code 200-299)
        if (!screenshotResponse.ok) {
            throw new Error('Error: cannot get screenshot, please try again');
        }

        const result = await screenshotResponse.json();
        if (result.status === 'success') {
            alert('Screenshot taken successfully');
           
        } else {
            alert('Error taking screenshot:', result.error);
            
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while taking the screenshot. Please try again.');
    }
});