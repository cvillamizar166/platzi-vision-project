from flask import request, jsonify, Response
import openai
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
def generate_image(prompt:str,quality: str = "standard")->str:
    '''
    Genera una imagen utilizando el modelo DALL-3 de OpenAI
    '''
    print(f"calidad {quality}")
    try:
        response = openai.images.generate(
            #model = "dall-e-3",
            model = "dall-e-2",
            prompt=prompt,
            quality=quality,
            n=1
        )

        print("Imagen generada correctamente")

        return response.data[0].url
    except Exception as e:
        print(f"Generacion de la imagen fallida:{str(e)}")

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
         # si el mensage contiene la propiedad imagen es que se ha adjuntado una para su procesamiento
         if 'image_data' in message:
               #Procesar la imagen
               content_part = [{"type":"text","text":message['content']}] #lo que solicito el usuario con la imagen

               for image_data_base64 in message['image_data']:
                   content_part.append({
                       "type":"image_url",
                       "image_url":{
                           "url": f"data:image/png,base64,{image_data_base64}"
                       }
                   })
               #print("contenido imagen")
               #print(content_part)
               formatted_messages.append({
                  "role": message["role"],
                  "content": content_part,
               })
         else:
               formatted_messages.append({
                  "role": message["role"],
                  "content": message['content'],
               })

      client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
      #definimos herramienta
      tools = [
          {
              "type": "function",
              "function":{
                  "name": "generate_image",
                  "description": "Cuando el usuario lo solicite, genera una imagen",
                  "parameters":{
                      "type":"object",
                      "properties":{
                          "prompt":{
                            "type":"string",
                            "description": "El prompt que generara la imagen"
                        },
                         "quality":{
                            "type":"string",
                            "description": "La calidad de la imagen deb ser standard'"
                        },
                      }
                  }
              }
          }
      ]


      def generate():
        #iteramos en las respuestas de la funcion
        accumulated_args = ""
        response = None
        current_tool_call_id = None
        while True:
            # esto indica que la conversacion debe continuar su curso
            if response is None:

                response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=formatted_messages,
                stream=True,
                tools=tools
                )


            #iteramos por cada pedazo de response asi es como se ve el stream
            for chunk in response:
                ##print("Respuesta chunk: ")
                ##print(chunk) # muestra cada parte de la respuesta
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content,
                                                'status':'streaming'})}\n\n"

                if chunk.choices[0].finish_reason == "stop":
                    yield f"data: {json.dumps({'status':"done"})}\n\n"  #retorno
                    break
                
                #identificamos en que momento se realiza un llamado a la herramienta
                if  chunk.choices[0].delta.tool_calls:
                    tool_call = chunk.choices[0].delta.tool_calls[0]

                    if tool_call.id and tool_call.function.name:
                        current_tool_call_id = tool_call.id
                    
                    if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                        accumulated_args += tool_call.function.arguments
                        print(f"Argumentos generados {tool_call.function.arguments}")

                    if accumulated_args.strip().endswith('}'):
                        try:
                            print("Iniciando la llamada a la funcion")
                            function_args = json.loads(accumulated_args)

                            if 'prompt'in function_args:
                                yield f"data: {json.dumps({'status':'generating_image'})}\n\n"

                                image_url = generate_image(prompt=function_args['prompt'], quality=function_args['quality'])
                                
                                #agregamos la url de la imagen al historial de mensajes, llamada a la funcion
                                formatted_messages.append({
                                        "role":"assistant",
                                        "content":None,
                                        "tool_calls":[{
                                            "id":current_tool_call_id,
                                            "function":{
                                                "name":"generate_image",
                                                "arguments":accumulated_args
                                            },
                                            "type": "function"
                                        }]
                                    }
                                )

                                #Agregamos la url de la imagen cuando ya la tenemos
                                formatted_messages.append({
                                    "role":"tool",
                                    "tool_call_id":current_tool_call_id,
                                    "content": image_url
                                })

                                #con esto volvemos ya que se genero la imagen
                                response = None
                                break
                        except:
                            pass


          
      return Response(generate(),mimetype="test/event-stream")
    

      pass

    
    except Exception as e:
        print(f"Chat request failed: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
