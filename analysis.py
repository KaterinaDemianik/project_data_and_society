from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
from datetime import datetime
import os
import matplotlib.pyplot as plt
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_FOLDER = os.path.join(PROJECT_ROOT, "test_results")

vader_analyzer = SentimentIntensityAnalyzer()

if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)


def analyze_sentiment(text):
    if not text or len(text.strip()) < 3:
        return 0.0

    try:
        vader_scores = vader_analyzer.polarity_scores(text)
        vader_sentiment = vader_scores['compound']
        return vader_sentiment
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return 0.0


def create_sentiment_chart(results, filename):
    if len(results) < 1:
        print("Not enough data for chart")
        return None

    conversation_msgs = []
    user_sentiments = []
    ai_sentiments = []

    for i, item in enumerate(results):
        question = item.get('question', '')
        answer = item.get('answer', '')

        if (answer) and ("ERROR" not in answer) and ("No response" not in answer):
            pair_label = f"{i + 1}"
            conversation_msgs.append(pair_label)

            user_sentiments.append(analyze_sentiment(question))
            ai_sentiments.append(analyze_sentiment(answer))

    if len(conversation_msgs) < 1:
        return None


    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('#f8f9fa')

    x_positions = np.arange(len(conversation_msgs))

    ax.plot(x_positions, user_sentiments,
            marker='o', linewidth=2.5, markersize=7,
            label='human messages', color='#B87C4C', alpha=0.85, zorder=3)

    ax.plot(x_positions, ai_sentiments,
            marker='o', linewidth=2.5, markersize=7,
            label='ai messages', color='#91C4C3', alpha=0.85, zorder=3)

    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1.5, zorder=1)

    ax.fill_between(x_positions, user_sentiments, ai_sentiments, alpha=0.1, color='gray', zorder=2)

    ax.set_title('Sentiment Viz', fontsize=13, fontweight='bold', pad=15)
    ax.set_ylabel('Sentiment Score', fontsize=11, fontweight='bold')
    ax.set_xlabel('Message', fontsize=11, fontweight='bold')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(conversation_msgs, fontsize=9)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_ylim(-1.1, 1.1)

    for i, (x, y_user) in enumerate(zip(x_positions, user_sentiments)):
        ax.annotate(f'{y_user:.2f}', (x, y_user), textcoords='offset points',
                    xytext=(0, 8), ha='center', fontsize=8, color='#2E86AB', fontweight='bold')

    for i, (x, y_ai) in enumerate(zip(x_positions, ai_sentiments)):
        ax.annotate(f'{y_ai:.2f}', (x, y_ai), textcoords='offset points',
                    xytext=(0, -12), ha='center', fontsize=8, color='#A23B72', fontweight='bold')

    plt.tight_layout()

    chart_path = os.path.join(RESULTS_FOLDER, filename)
    plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close()

    return chart_path


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        results = data.get('results', [])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        csv_filename = f"chat_{timestamp}.csv"
        csv_filepath = os.path.join(RESULTS_FOLDER, csv_filename)

        with open(csv_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'user', 'message', 'msg_length'])

            for item in results:
                question = item.get('question', '')
                answer = item.get('answer', '')

                writer.writerow([
                    item.get('timestamp', ''),
                    'human',
                    question,
                    len(question.split())
                ])

                writer.writerow([
                    item.get('timestamp', ''),
                    'ai',
                    answer,
                    len(answer.split())
                ])

        chart_filename = f"sentiment_viz_{timestamp}.png"
        chart_path = create_sentiment_chart(results, chart_filename)

        total_user_sentiment = 0
        total_ai_sentiment = 0
        ai_responses = 0
        sentiment_gaps = []

        for idx, item in enumerate(results, 1):
            question = item.get('question', '')
            answer = item.get('answer', '')

            if (answer) and ("ERROR" not in answer) and ("No response" not in answer):
                user_sentiment = analyze_sentiment(question)
                ai_sentiment = analyze_sentiment(answer)

                total_user_sentiment += user_sentiment
                total_ai_sentiment += ai_sentiment
                sentiment_gaps.append(abs(user_sentiment - ai_sentiment))
                ai_responses += 1


        avg_user_sentiment = total_user_sentiment / ai_responses if ai_responses else 0
        avg_ai_sentiment = total_ai_sentiment / ai_responses if ai_responses else 0
        avg_sentiment_gap = np.mean(sentiment_gaps) if sentiment_gaps else 0

        print(f"Total conversations: {len(results)}")
        print(f"AI responses analyzed: {ai_responses}")
        print(f"Avg user sentiment: {avg_user_sentiment:.3f}")
        print(f"Avg AI sentiment: {avg_ai_sentiment:.3f}")
        print(f"Avg sentiment gap: {avg_sentiment_gap:.3f}")
        if chart_path:
            print(f"Chart file: {chart_filename}")
        print(f"{'=' * 60}\n")

        return jsonify({
            'status': 'success',
            'total_questions': len(results),
            'ai_responses': ai_responses,
            'average_user_sentiment': round(avg_user_sentiment, 3),
            'average_ai_sentiment': round(avg_ai_sentiment, 3),
            'average_sentiment_gap': round(avg_sentiment_gap, 3),
            'csv_file': csv_filename,
            'chart_file': chart_filename if chart_path else None,
            'message': 'Analysis complete with sentiment chart'
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'server': 'Python Analysis Server',
        'results_folder': RESULTS_FOLDER,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("Server running on http://127.0.0.1:5001")

    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)
        print(f"Created results folder: {RESULTS_FOLDER}")

    app.run(debug=True, port=5001)