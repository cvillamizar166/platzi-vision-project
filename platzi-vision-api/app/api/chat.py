from flask import request, jsonify, Response
import openai
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
def chat():
    try:
      data = request.json
      print("Json enviado inicialmente")
      print(data)
      formatted_messages = [
         {
            "role": "system",
            "content": "Eres un asistente llamado PlatziVision. Responde las preguntas de los usuarios con claridad."
         }
      ]

      for message in data['messages']:
         formatted_messages.append({
            "role": message["role"],
            "content": message['content'],
         })

      client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

      response = client.chat.completions.create(
         model="gpt-4o-mini",
         messages=formatted_messages,
         stream=True
      )

      def generate():
        #iteramos por cada pedazo de response asi es como se ve el stream
        for chunk in response:
          print("Respuesta chunk: ")
          print(chunk) # muestra cada parte de la respuesta
          if chunk.choices[0].delta.content:
              yield f"data: {json.dumps({'content': chunk.choices[0].delta.content,
                                        'status':'streaming'})}\n\n"

          if chunk.choices[0].finish_reason == "stop":
              yield f"data: {json.dumps({'status':"done"})}\n\n"  #retorno
              break
          
      return Response(generate(),mimetype="test/event-stream")
    

      pass

    
    except Exception as e:
        print(f"Chat request failed: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
