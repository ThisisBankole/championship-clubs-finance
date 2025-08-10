# app/services/azure_search/manager.py
import os
from typing import Dict, Any, List, Optional
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType,
    SearchIndexer, SearchIndexerDataSourceConnection, SearchIndexerDataContainer,
    SearchIndexerSkillset, WebApiSkill, DocumentExtractionSkill,
    InputFieldMappingEntry, OutputFieldMappingEntry, FieldMapping,
    IndexingParameters, CorsOptions
)
from azure.core.credentials import AzureKeyCredential
import structlog

logger = structlog.get_logger()

class AzureSearchManager:
    """Manages Azure Search infrastructure programmatically"""
    
    def __init__(self):
        # Get configuration from environment
        self.endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        self.key = os.getenv('AZURE_SEARCH_KEY')
        self.storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'clubs-fin')
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        
        if not all([self.endpoint, self.key]):
            raise ValueError("Azure Search endpoint and key must be configured")
        
        # Initialize clients
        credential = AzureKeyCredential(self.key)
        self.index_client = SearchIndexClient(self.endpoint, credential)
        self.indexer_client = SearchIndexerClient(self.endpoint, credential)
        
        # Resource naming - using simple approach
        self.datasource_name = "football-financials-simple"
        self.index_name = "football-financials-simple"
        self.skillset_name = "football-financials-simple"
        self.indexer_name = "football-financials-simple"
    
    # Step 1: Create Data Source
    def create_data_source(self) -> str:
        """Create connection to blob storage"""
        
        logger.info("Creating data source", name=self.datasource_name)
        
        data_source = SearchIndexerDataSourceConnection(
            name=self.datasource_name,
            type="azureblob",
            connection_string=self.storage_connection,
            container=SearchIndexerDataContainer(
                name=self.container_name,
                query=None  # Process all blobs
            ),
            description="Football club financial documents from blob storage"
        )
        
        try:
            result = self.indexer_client.create_or_update_data_source_connection(data_source)
            logger.info("Data source created successfully", name=self.datasource_name)
            return self.datasource_name
            
        except Exception as e:
            logger.error("Failed to create data source", error=str(e))
            raise
    
    # Step 2: Create Search Index  
    def create_search_index(self) -> str:
        """Create the search index with proper schema"""
        
        logger.info("Creating search index", name=self.index_name)
        
        fields = [
            # Document identification
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SimpleField(
                name="metadata_storage_path", 
                type=SearchFieldDataType.String,
                filterable=False
            ),
            SimpleField(
                name="metadata_storage_name",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            
            # Club metadata (from your existing metadata extractor)
            SearchableField(
                name="club_name",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
                facetable=True
            ),
            SimpleField(
                name="company_number",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="accounts_year_end",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
                facetable=True
            ),
            
            # Keep clean extracted content for debugging
            SearchableField(
                name="extracted_content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            
            # Core financial data
            SimpleField(
                name="revenue",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                facetable=True
            ),
            SimpleField(
                name="turnover", 
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                facetable=True
            ),
            SimpleField(
                name="total_assets",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="net_assets",
                type=SearchFieldDataType.Double, 
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="cash_at_bank",
                type=SearchFieldDataType.Double,
                filterable=True, 
                sortable=True
            ),
            SimpleField(
                name="operating_profit",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            
            # Football-specific financials
            SimpleField(
                name="broadcasting_revenue",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="commercial_revenue", 
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="matchday_revenue",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="player_wages",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="player_trading_income",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="player_amortization",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            
            # Additional financial fields
            SimpleField(
                name="total_liabilities",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="cash_and_cash_equivalents",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="creditors_due_within_one_year",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="creditors_due_after_one_year", 
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="profit_loss_before_tax",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="other_staff_costs",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="stadium_costs",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="administrative_expenses",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="agent_fees",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            )
        ]
        
        # Create index with CORS for web access
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            cors_options=CorsOptions(
                allowed_origins=["*"],
                max_age_in_seconds=60
            )
        )
        
        try:
            result = self.index_client.create_or_update_index(index)
            logger.info("Search index created successfully", name=self.index_name)
            return self.index_name
            
        except Exception as e:
            logger.error("Failed to create search index", error=str(e))
            raise
    
    # Step 3: Create Skillset with Document Extraction (following MS Learn patterns)
    def create_skillset(self, use_combined_extraction: bool = True) -> str:
        """Create skillset using Document Extraction skill (built-in, reliable)"""
        
        logger.info("Creating skillset with Document Extraction skill", name=self.skillset_name)
        
        skills = []
        
        # 1. Document Extraction Skill (built-in - no import issues)
        document_extraction_skill = DocumentExtractionSkill(
            name="document-extraction",
            description="Extract text content from PDF documents",
            context="/document",
            parsing_mode="default",  # Perfect for PDFs
            data_to_extract="contentAndMetadata",  # Get text + metadata
            configuration={
                "imageAction": "generateNormalizedImages",  # Extract images too
                "normalizedImageMaxWidth": 2000,
                "normalizedImageMaxHeight": 2000
            },
            inputs=[
                InputFieldMappingEntry(
                    name="file_data",
                    source="/document/file_data"
                )
            ],
            outputs=[
                OutputFieldMappingEntry(
                    name="content",
                    target_name="extracted_content"  # Clean text output
                ),
                OutputFieldMappingEntry(
                    name="normalized_images", 
                    target_name="extracted_images"
                )
            ]
        )
        skills.append(document_extraction_skill)
        
        # 2. Club Metadata Extraction (your existing skill)
        metadata_skill = WebApiSkill(
            name="extract-club-metadata",
            description="Extract club info from blob path",
            context="/document", 
            uri=f"{self.api_base_url}/api/v1/skillsets/extract-club-metadata",
            http_method="POST",
            timeout="PT1M",
            batch_size=10,
            inputs=[
                InputFieldMappingEntry(
                    name="blob_path",
                    source="/document/metadata_storage_path"
                )
            ],
            outputs=[
                OutputFieldMappingEntry(name="company_number", target_name="company_number"),
                OutputFieldMappingEntry(name="club_name", target_name="club_name"), 
                OutputFieldMappingEntry(name="accounts_year_end", target_name="accounts_year_end")
            ]
        )
        skills.append(metadata_skill)
        
        # 3. Financial Extraction (updated to use clean content)
        if use_combined_extraction:
            financial_skill = WebApiSkill(
                name="extract-financials",
                description="Extract financial data from clean text content",
                context="/document",
                uri=f"{self.api_base_url}/api/v1/financial-extraction/extract-financials", 
                http_method="POST",
                timeout="PT5M",
                batch_size=1,
                inputs=[
                    InputFieldMappingEntry(
                        name="text",
                        source="/document/extracted_content"  # Use clean content from Document Extraction
                    )
                ],
                outputs=[
                    OutputFieldMappingEntry(name="revenue", target_name="revenue"),
                    OutputFieldMappingEntry(name="turnover", target_name="turnover"),
                    OutputFieldMappingEntry(name="total_assets", target_name="total_assets"),
                    OutputFieldMappingEntry(name="net_assets", target_name="net_assets"),
                    OutputFieldMappingEntry(name="cash_at_bank", target_name="cash_at_bank"),
                    OutputFieldMappingEntry(name="operating_profit", target_name="operating_profit"),
                    OutputFieldMappingEntry(name="broadcasting_revenue", target_name="broadcasting_revenue"),
                    OutputFieldMappingEntry(name="commercial_revenue", target_name="commercial_revenue"),
                    OutputFieldMappingEntry(name="matchday_revenue", target_name="matchday_revenue"),
                    OutputFieldMappingEntry(name="player_wages", target_name="player_wages"),
                    OutputFieldMappingEntry(name="player_trading_income", target_name="player_trading_income"),
                    OutputFieldMappingEntry(name="player_amortization", target_name="player_amortization"),
                    OutputFieldMappingEntry(name="total_liabilities", target_name="total_liabilities"),
                    OutputFieldMappingEntry(name="cash_and_cash_equivalents", target_name="cash_and_cash_equivalents"),
                    OutputFieldMappingEntry(name="creditors_due_within_one_year", target_name="creditors_due_within_one_year"),
                    OutputFieldMappingEntry(name="creditors_due_after_one_year", target_name="creditors_due_after_one_year"),
                    OutputFieldMappingEntry(name="profit_loss_before_tax", target_name="profit_loss_before_tax"),
                    OutputFieldMappingEntry(name="other_staff_costs", target_name="other_staff_costs"),
                    OutputFieldMappingEntry(name="stadium_costs", target_name="stadium_costs"),
                    OutputFieldMappingEntry(name="administrative_expenses", target_name="administrative_expenses"),
                    OutputFieldMappingEntry(name="agent_fees", target_name="agent_fees")
                ]
            )
            skills.append(financial_skill)
        
        # Create skillset
        skillset = SearchIndexerSkillset(
            name=self.skillset_name,
            description="Simple skillset following MS Learn patterns",
            skills=skills
        )
        
        try:
            result = self.indexer_client.create_or_update_skillset(skillset)
            logger.info("Skillset created successfully", name=self.skillset_name)
            return self.skillset_name
            
        except Exception as e:
            logger.error("Failed to create skillset", error=str(e))
            raise
    
    # Step 4: Create Indexer
    def create_indexer(self) -> str:
        """Create indexer to orchestrate the pipeline"""
        
        logger.info("Creating indexer", name=self.indexer_name)
        
        # Field mappings (blob metadata to index fields)
        field_mappings = [
            FieldMapping(
                source_field_name="metadata_storage_path", 
                target_field_name="metadata_storage_path"
            ),
            FieldMapping(
                source_field_name="metadata_storage_name",
                target_field_name="metadata_storage_name"
            )
        ]
        
        # Output field mappings (skillset outputs to index fields)
        output_field_mappings = [
            # Clean extracted content
            FieldMapping(
                source_field_name="/document/extracted_content",
                target_field_name="extracted_content"
            ),
            
            # Club metadata
            FieldMapping(
                source_field_name="/document/company_number",
                target_field_name="company_number"
            ),
            FieldMapping(
                source_field_name="/document/club_name", 
                target_field_name="club_name"
            ),
            FieldMapping(
                source_field_name="/document/accounts_year_end",
                target_field_name="accounts_year_end"
            ),
            
            # Financial data outputs
            FieldMapping(source_field_name="/document/revenue", target_field_name="revenue"),
            FieldMapping(source_field_name="/document/turnover", target_field_name="turnover"),
            FieldMapping(source_field_name="/document/total_assets", target_field_name="total_assets"),
            FieldMapping(source_field_name="/document/net_assets", target_field_name="net_assets"),
            FieldMapping(source_field_name="/document/cash_at_bank", target_field_name="cash_at_bank"),
            FieldMapping(source_field_name="/document/operating_profit", target_field_name="operating_profit"),
            FieldMapping(source_field_name="/document/broadcasting_revenue", target_field_name="broadcasting_revenue"),
            FieldMapping(source_field_name="/document/commercial_revenue", target_field_name="commercial_revenue"),
            FieldMapping(source_field_name="/document/matchday_revenue", target_field_name="matchday_revenue"),
            FieldMapping(source_field_name="/document/player_wages", target_field_name="player_wages"),
            FieldMapping(source_field_name="/document/player_trading_income", target_field_name="player_trading_income"),
            FieldMapping(source_field_name="/document/player_amortization", target_field_name="player_amortization"),
            FieldMapping(source_field_name="/document/total_liabilities", target_field_name="total_liabilities"),
            FieldMapping(source_field_name="/document/cash_and_cash_equivalents", target_field_name="cash_and_cash_equivalents"),
            FieldMapping(source_field_name="/document/creditors_due_within_one_year", target_field_name="creditors_due_within_one_year"),
            FieldMapping(source_field_name="/document/creditors_due_after_one_year", target_field_name="creditors_due_after_one_year"),
            FieldMapping(source_field_name="/document/profit_loss_before_tax", target_field_name="profit_loss_before_tax"),
            FieldMapping(source_field_name="/document/other_staff_costs", target_field_name="other_staff_costs"),
            FieldMapping(source_field_name="/document/stadium_costs", target_field_name="stadium_costs"),
            FieldMapping(source_field_name="/document/administrative_expenses", target_field_name="administrative_expenses"),
            FieldMapping(source_field_name="/document/agent_fees", target_field_name="agent_fees")
        ]
        
        # Indexing parameters
        parameters = IndexingParameters(
            batch_size=1,  # Process one document at a time
            max_failed_items=5,
            max_failed_items_per_batch=1,
            configuration={
                "dataToExtract": "contentAndMetadata",
                "imageAction": "generateNormalizedImages", 
                "allowSkillsetToReadFileData": True
            }
        )
        
        # Create indexer
        indexer = SearchIndexer(
            name=self.indexer_name,
            description="Process football club financial documents",
            data_source_name=self.datasource_name,
            target_index_name=self.index_name,
            skillset_name=self.skillset_name,
            field_mappings=field_mappings,
            output_field_mappings=output_field_mappings,
            parameters=parameters
        )
        
        try:
            result = self.indexer_client.create_or_update_indexer(indexer)
            logger.info("Indexer created successfully", name=self.indexer_name)
            return self.indexer_name
            
        except Exception as e:
            logger.error("Failed to create indexer", error=str(e))
            raise
    
    # Utility methods
    def run_indexer(self) -> bool:
        """Run the indexer"""
        try:
            self.indexer_client.run_indexer(self.indexer_name)
            logger.info("Indexer started", name=self.indexer_name)
            return True
        except Exception as e:
            logger.error("Failed to run indexer", error=str(e))
            return False
    
    def get_indexer_status(self) -> Dict[str, Any]:
        """Get indexer execution status"""
        try:
            status = self.indexer_client.get_indexer_status(self.indexer_name)
            
            # Handle the actual structure of the status object
            result = {
                "indexer_name": self.indexer_name,
                "status": str(status.status) if hasattr(status, 'status') and status.status else "unknown"
            }
            
            # Get last execution result if available
            if hasattr(status, 'last_result') and status.last_result:
                last_result = status.last_result
                result["last_result"] = {
                    "status": str(last_result.status) if hasattr(last_result, 'status') else "unknown",
                    "start_time": str(last_result.start_time) if hasattr(last_result, 'start_time') else None,
                    "end_time": str(last_result.end_time) if hasattr(last_result, 'end_time') else None,
                    "item_count": getattr(last_result, 'item_count', 0),
                    "failed_item_count": getattr(last_result, 'failed_item_count', 0),
                    "initial_tracking_state": str(getattr(last_result, 'initial_tracking_state', '')),
                    "final_tracking_state": str(getattr(last_result, 'final_tracking_state', ''))
                }
                
                # Get error details if any
                if hasattr(last_result, 'errors') and last_result.errors:
                    result["last_result"]["errors"] = [str(error) for error in last_result.errors]
            
            # Get execution history if available
            if hasattr(status, 'execution_history') and status.execution_history:
                result["execution_history"] = []
                for execution in status.execution_history[:3]:  # Last 3 executions
                    exec_info = {
                        "status": str(execution.status) if hasattr(execution, 'status') else "unknown",
                        "start_time": str(execution.start_time) if hasattr(execution, 'start_time') else None,
                        "end_time": str(execution.end_time) if hasattr(execution, 'end_time') else None
                    }
                    if hasattr(execution, 'errors') and execution.errors:
                        exec_info["errors"] = [str(error) for error in execution.errors]
                    result["execution_history"].append(exec_info)
            
            return result
            
        except Exception as e:
            logger.error("Failed to get indexer status", error=str(e))
            return {"error": str(e)}
    
    def delete_all_resources(self):
        """Delete all created resources (for cleanup)"""
        resources = [
            (self.indexer_client.delete_indexer, self.indexer_name, "indexer"),
            (self.indexer_client.delete_skillset, self.skillset_name, "skillset"),
            (self.index_client.delete_index, self.index_name, "index"),
            (self.indexer_client.delete_data_source_connection, self.datasource_name, "data source")
        ]
        
        for delete_func, resource_name, resource_type in resources:
            try:
                delete_func(resource_name)
                logger.info(f"Deleted {resource_type}", name=resource_name)
            except Exception as e:
                logger.warning(f"Failed to delete {resource_type}", name=resource_name, error=str(e))