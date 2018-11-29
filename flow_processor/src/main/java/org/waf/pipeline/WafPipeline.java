package org.waf.pipeline;

import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.options.Description;
import org.apache.beam.sdk.options.Default;
import org.apache.beam.sdk.options.DefaultValueFactory;
import org.apache.beam.sdk.options.PipelineOptions;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.*;
import org.apache.beam.sdk.transforms.windowing.*;
import org.apache.beam.sdk.values.*;
import org.apache.beam.sdk.io.gcp.pubsub.PubsubIO;

import org.joda.time.Duration;

import java.util.*;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableRow;
import com.google.api.services.bigquery.model.TableSchema;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;

public class WafPipeline {

    public interface WafPipelineOptions extends PipelineOptions {
        @Description("Project name")
        @Default.String("None")
        String getProjectName();

        void setProjectName(String value);
    }

    public static void main(String[] args) {
        WafPipelineOptions options = PipelineOptionsFactory.fromArgs(args).withValidation().as(WafPipelineOptions.class);

        Pipeline p = Pipeline.create(options);

        PCollection<String> input = p.apply("ReadFromPubSub", PubsubIO.readStrings().fromSubscription("projects/" + options.getProjectName() + "/subscriptions/beam-sub"));
        PCollection<String> windowedLines = input.apply(Window.<String>into(FixedWindows.of(Duration.standardSeconds(1))));

        PCollection<Map<String, String>> documents = windowedLines.apply(ParDo.of(new EventParser.ParseAndCreateDocumentFn()));

        PCollection<Map<String, String>> enriched_documents = documents.apply("Shard documents", ParDo.of(new Utils.FakeKvPair())).apply("EnrichDocuments", ParDo.of(new Enrichment.ProcessEnrichment()));

        enriched_documents.apply("PerformCorrelation", Window.<Map<String, String>>into(SlidingWindows.of(Duration.standardMinutes(1)).
                every(Duration.standardSeconds(1)))).apply("FindWafAttack", new Correlations.TrackWaf())
                .apply(PubsubIO.writeStrings().to("projects/" + options.getProjectName() + "/topics/waf_alerts"));


        PCollection<String> json_documents = enriched_documents.apply(ParDo.of(new Utils.MapToJson()));
        json_documents.apply(PubsubIO.writeStrings().to("projects/" + options.getProjectName() + "/topics/enriched_events"));

        PCollection<TableRow> quotes = json_documents.apply(ParDo.of(new BigQuery.JsonToTableRow()));

        List<TableFieldSchema> fields = new ArrayList<>();
        fields.add(new TableFieldSchema().setName("epoch").setType("STRING"));
        fields.add(new TableFieldSchema().setName("raw_data").setType("STRING"));
        TableSchema schema = new TableSchema().setFields(fields);

        quotes.apply(BigQueryIO.writeTableRows()
              .to(options.getProjectName() + ":raw_dataset.raw_data")
              .withSchema(schema)
              .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND));

        p.run().waitUntilFinish();
    }
}