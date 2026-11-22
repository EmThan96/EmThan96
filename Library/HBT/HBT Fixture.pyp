<?xml version="1.0" encoding="utf-8"?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>HBT\HBTFixture.py</Name>
        <Title>HBT Fixture</Title>
        <Version>1.0</Version>
        <ReadLastInput>True</ReadLastInput>
    </Script>
    <Constants>
        <Constant>
            <Name>REF_POINT</Name>
            <Value>1</Value>
            <ValueType>Integer</ValueType>
        </Constant>
        <Constant>
            <Name>DIR_POINT</Name>
            <Value>2</Value>
            <ValueType>Integer</ValueType>
        </Constant>
    </Constants>
    <Page>
        <Name>HBTPage</Name>
        <Text>HBT</Text>
        <Parameters>
            <Parameter>
                <Name>ProductExp</Name>
                <Text>Product</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>ProductType</Name>
                        <Text>Type</Text>
                        <Value>HBT-1R</Value>
                        <ValueList>TypeList</ValueList>
                        <ValueType>StringComboBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>TypeName</Name>
                        <Text>Description</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>Diameter</Name>
                        <Text>Bar diameter [mm]</Text>
                        <Value>12</Value>
                        <ValueList>DiameterList</ValueList>
                        <ValueType>StringComboBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>Spacing</Name>
                        <Text>Bar spacing [mm]</Text>
                        <Value>150</Value>
                        <ValueList>SpacingList</ValueList>
                        <ValueType>StringComboBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>BoxLength</Name>
                        <Text>Box length [mm]</Text>
                        <Value>1250</Value>
                        <ValueList>BoxLengthList</ValueList>
                        <ValueType>StringComboBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>Article</Name>
                        <Text>Fixture name</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>DataExp</Name>
                <Text>Catalogue data</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>BoxWidth</Name>
                        <Text>Box width</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>BoxDepth</Name>
                        <Text>Box depth</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>AnchorLength</Name>
                        <Text>Anchor length (1st pour)</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>ConnectionLength</Name>
                        <Text>Connection length (2nd pour)</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>RowDistance</Name>
                        <Text>Row distance</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>BarCount</Name>
                        <Text>Number of bars</Text>
                        <Value>0</Value>
                        <ValueType>Integer</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>InfoText</Name>
                        <Text>Info</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>CatalogueFile</Name>
                        <Text>Catalogue file (empty = default)</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>PlacementExp</Name>
                <Text>Placement</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>FacePlane</Name>
                        <Text>Formwork face</Text>
                        <Value>2</Value>
                        <ValueType>RadioButtonGroup</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>FaceHorizontal</Name>
                                <Text>Horizontal face</Text>
                                <Value>1</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>FaceVerticalBoxHoriz</Name>
                                <Text>Vertical face, box horizontal</Text>
                                <Value>2</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>FaceVerticalBoxVert</Name>
                                <Text>Vertical face, box vertical</Text>
                                <Value>3</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>FlipSide</Name>
                        <Text>Flip anchor side</Text>
                        <Value>False</Value>
                        <ValueType>CheckBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>BarState</Name>
                        <Text>Bar state</Text>
                        <Value>1</Value>
                        <ValueType>RadioButtonGroup</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>BarsStraightened</Name>
                                <Text>Straightened (installed)</Text>
                                <Value>1</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>BarsDelivered</Name>
                                <Text>Bent in box (delivered)</Text>
                                <Value>2</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>CutBoxVolume</Name>
                        <Text>Cut box volume from precast element</Text>
                        <Value>False</Value>
                        <ValueType>CheckBox</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>FormatExp</Name>
                <Text>Format</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>CommonProp</Name>
                        <Text></Text>
                        <Value></Value>
                        <ValueType>CommonProperties</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>BarColor</Name>
                        <Text>Bar color</Text>
                        <Value>6</Value>
                        <ValueType>Color</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
        </Parameters>
    </Page>
    <Page>
        <Name>__HiddenPage__</Name>
        <Text/>
        <Parameters>
            <Parameter>
                <Name>InputMode</Name>
                <Value>1</Value>
                <ValueType>Integer</ValueType>
            </Parameter>
            <Parameter>
                <Name>TypeList</Name>
                <Value>HBT-1R</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>DiameterList</Name>
                <Value>12</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>SpacingList</Name>
                <Value>150</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>BoxLengthList</Name>
                <Value>1250</Value>
                <ValueType>String</ValueType>
            </Parameter>
        </Parameters>
    </Page>
</Element>
