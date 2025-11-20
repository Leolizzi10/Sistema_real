#include <WiFi.h>
#include <Arduino.h>

// --- PINOS ---
#define LED_WARN 2
#define LED_OKAY 4
#define INTERVALO_SCAN_MS 4000

// --- RTOS ---
QueueHandle_t filaWifi;
SemaphoreHandle_t travaListaSegura;

// Redes permitidas (ALTERADAS)
String redesPermitidas[] = {
  "AlphaNet-Pro",
  "SecureOps_24",
  "BuildingWiFi-3F",
  "CorpZone_Main",
  "EngLab-Private"
};
const int QTDE_REDES_PERMITIDAS = 5;

// Redes simuladas (ALTERADAS)
String listaSimulada[] = {
  "AlphaNet-Pro",
  "CityFree_Wifi",
  "SecureOps_24",
  "HotelLobbyNet",
  "BuildingWiFi-3F",
  "EngLab-Private"
};
int indiceSimulacao = 0;

// -----------------------------
// TAREFA 1 – Leitor de SSID
// -----------------------------
void tarefaEscaneamento(void *params)
{
  while (1)
  {
    String ssidAtual = listaSimulada[indiceSimulacao];
    indiceSimulacao = (indiceSimulacao + 1) % 6;

    if (xQueueSend(filaWifi, &ssidAtual, pdMS_TO_TICKS(1000)) != pdTRUE) {
      Serial.println("[ERRO] Fila cheia – SSID descartado!");
    }

    Serial.println("[SCAN] SSID coletado: " + ssidAtual);
    vTaskDelay(pdMS_TO_TICKS(INTERVALO_SCAN_MS));
  }
}

// -----------------------------
// TAREFA 2 – Verificador
// -----------------------------
void tarefaVerificacao(void *params)
{
  String recebido;
  int contadorTimeout = 0;

  while (1)
  {
    if (xQueueReceive(filaWifi, &recebido, pdMS_TO_TICKS(5000)) == pdTRUE)
    {
      contadorTimeout = 0;
      bool redeAutorizada = false;

      if (xSemaphoreTake(travaListaSegura, pdMS_TO_TICKS(1000)) == pdTRUE)
      {
        for (int i = 0; i < QTDE_REDES_PERMITIDAS; i++)
        {
          if (recebido == redesPermitidas[i]) redeAutorizada = true;
        }
        xSemaphoreGive(travaListaSegura);
      }
      else
      {
        Serial.println("[ERRO] Falha ao acessar lista segura (mutex travado)");
      }

      if (!redeAutorizada)
      {
        Serial.printf("[%lu ms] ⚠️ REDE BLOQUEADA: %s\n", millis(), recebido.c_str());
        digitalWrite(LED_OKAY, LOW);

        for (int i = 0; i < 3; i++)
        {
          digitalWrite(LED_WARN, HIGH);
          vTaskDelay(pdMS_TO_TICKS(200));
          digitalWrite(LED_WARN, LOW);
          vTaskDelay(pdMS_TO_TICKS(200));
        }
      }
      else
      {
        Serial.printf("[%lu ms] ✔️ Rede autorizada: %s\n", millis(), recebido.c_str());

        for (int i = 0; i < 2; i++)
        {
          digitalWrite(LED_OKAY, HIGH);
          vTaskDelay(pdMS_TO_TICKS(150));
          digitalWrite(LED_OKAY, LOW);
          vTaskDelay(pdMS_TO_TICKS(150));
        }
      }
    }
    else
    {
      contadorTimeout++;
      Serial.printf("[AVISO] Nenhum SSID recebido (timeout %d)\n", contadorTimeout);

      if (contadorTimeout >= 3)
      {
        Serial.println("[RECUPERAÇÃO] Reiniciando devido à inatividade...");
        esp_restart();
      }
    }
  }
}

// -----------------------------
// TAREFA 3 – Entrada serial
// -----------------------------
void tarefaEntrada(void *params)
{
  while (1)
  {
    if (Serial.available())
    {
      char comando = Serial.read();
      if (comando == 'r')
      {
        Serial.println("[COMANDO] Avanço manual do índice de SSID.");
        indiceSimulacao = (indiceSimulacao + 1) % 6;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(200));
  }
}

// -----------------------------
// SETUP
// -----------------------------
void setup()
{
  Serial.begin(115200);

  pinMode(LED_WARN, OUTPUT);
  pinMode(LED_OKAY, OUTPUT);

  filaWifi = xQueueCreate(5, sizeof(String));
  travaListaSegura = xSemaphoreCreateMutex();

  if (filaWifi == NULL || travaListaSegura == NULL)
  {
    Serial.println("[ERRO] Falha ao criar fila ou mutex!");
    while (1);
  }

  xTaskCreate(tarefaEscaneamento, "escaneador", 4096, NULL, 2, NULL);
  xTaskCreate(tarefaVerificacao, "verificador", 4096, NULL, 3, NULL);
  xTaskCreate(tarefaEntrada, "entrada", 4096, NULL, 1, NULL);

  Serial.println("[SISTEMA] Ativado – Monitor Wi-Fi (modo teste)");
}

void loop() {}
