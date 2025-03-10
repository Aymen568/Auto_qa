// Load website into iframe
document.getElementById('loadButton').addEventListener('click', async function () {
    
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
            console.log("1");
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
            feedbackBox.textContent = feedback.substring(0, 200); // Limit feedback to 200 words
        }
    }

    const url = document.getElementById('urlInput').value;
    if (url) {
        document.getElementById('websiteFrame').src = url;
    
        // Fetch HTML feedback and update chart/feedback box
        get_feedback('http://127.0.0.1:5000/evaluate_html', url)
            .then(({ score: html_score, feedback: html_feedback }) => {
                console.log('HTML Score:', html_score);
                console.log('HTML Feedback:', html_feedback);
                updateChart('chart1', 'score1', html_score); // Update HTML chart
                updateFeedbackBox('html-feedback', html_feedback); // Update HTML feedback box
            })
            .catch(error => {
                console.error('Error fetching HTML feedback:', error);
            });
    
        // Fetch Security feedback and update chart/feedback box
        get_feedback('http://127.0.0.1:5000/evaluate_security', url)
            .then(({ score: app_security_score, feedback: app_security_feedback }) => {
                console.log('Security Score:', app_security_score);
                console.log('Security Feedback:', app_security_feedback);
                updateChart('chart3', 'score3', app_security_score); // Update Security chart
                updateFeedbackBox('app-security-feedback', app_security_feedback); // Update Security feedback box
            })
            .catch(error => {
                console.error('Error fetching Security feedback:', error);
            });
    
        // Fetch User Experience feedback and update chart/feedback box
        get_feedback('http://127.0.0.1:5000/evaluate_user_experience', url)
            .then(({ score: user_experience_score, feedback: user_experience_feedback }) => {
                console.log('User Experience Score:', user_experience_score);
                console.log('User Experience Feedback:', user_experience_feedback);
                updateChart('chart2', 'score2', user_experience_score); // Update User Experience chart
                updateFeedbackBox('user-experience-feedback', user_experience_feedback); // Update User Experience feedback box
            })
            .catch(error => {
                console.error('Error fetching User Experience feedback:', error);
            });
    } else {
        alert('Please enter a valid URL.');
    }
});