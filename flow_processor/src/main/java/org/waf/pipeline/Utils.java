package org.waf.pipeline;
import com.google.gson.Gson;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.util.Map;
import java.util.Random;

public class Utils {
    static class MapToJson extends DoFn<Map<String, String>, String> {
        @ProcessElement
        public void processElement(ProcessContext c) {
            Map<String, String> document = c.element();

            Gson gsonObj = new Gson();
            String json_string = gsonObj.toJson(document);

            c.output(json_string);
        }
    }

    public static class FakeKvPair extends DoFn<Map<String, String>, KV<String, Map<String, String>>> {
        @ProcessElement
        public void processElement(ProcessContext c) {
            Random r = new Random();
            Integer randomInt;
            randomInt = r.nextInt(10) + 1; // this needs to be adjusted depending on size
            c.output(KV.of(randomInt.toString(), c.element()));
        }
    }

    public static String sendPOST(HttpURLConnection con, String data) throws IOException {
        con.setRequestMethod("POST");
        con.setRequestProperty("User-Agent", "DataFlowRunner");

        con.setDoOutput(true);
        OutputStream os = con.getOutputStream();
        os.write(data.getBytes());
        os.flush();
        os.close();

        int responseCode = con.getResponseCode();
        if (responseCode == HttpURLConnection.HTTP_OK) {
            BufferedReader in = new BufferedReader(new InputStreamReader(con.getInputStream()));
            String inputLine;
            StringBuffer response = new StringBuffer();

            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }
            in.close();

            return response.toString();
        } else {
            return "{\"error\":\"sendPostFailed\", \"status\":\"unknown\"}";
        }
    }
}