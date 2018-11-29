package org.waf.pipeline;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.transforms.DoFn;

public class BigQuery {
    static class JsonToTableRow extends DoFn<String, TableRow> {

        @ProcessElement
        public void processElement(ProcessContext c) {
            String json_document = c.element();

            long unixTime = System.currentTimeMillis() / 1000L;

            TableRow row = new TableRow();
            row.set("epoch", unixTime);
            row.set("raw_data", json_document);

            c.output(row);
        }
    }

}
